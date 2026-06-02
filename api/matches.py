# -*- coding: utf-8 -*-
"""Vercel serverless function: GET /api/matches
ขูดข้อมูลสดจาก tournamentsoftware -> ส่ง JSON ให้เว็บ (สด 100% ไม่พึ่ง Google Sheet).

query ?fresh=1  -> ปิด CDN cache (บังคับดึงสดทันที เมื่อผู้ใช้กดปุ่ม 🔄)
"""
import os, sys, json, urllib.parse
from http.server import BaseHTTPRequestHandler

# ให้ import scraper.py (อยู่ที่ root ของ repo) ได้ — Vercel bundle ไฟล์ทั้งโปรเจกต์ให้อยู่แล้ว
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def build_payload():
    from scraper import scrape, to_web  # lazy import (กัน build-time detection ล้ม)
    data = scrape(use_cache=False)
    matches = data.get("matches", [])
    if len(matches) < 10:
        raise RuntimeError(f"scraped too few matches ({len(matches)}) — refusing to serve")
    return to_web(data)                        # สด 100% จากต้นทาง (เลิก merge Google Sheet)


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        qs = urllib.parse.urlparse(self.path).query
        fresh = urllib.parse.parse_qs(qs).get("fresh", ["0"])[0] == "1"
        try:
            payload = build_payload()
            body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            if fresh:
                self.send_header("Cache-Control", "no-store, max-age=0")
            else:
                self.send_header("Cache-Control", "public, s-maxage=60, stale-while-revalidate=120")
            self.end_headers()
            self.wfile.write(body)
        except Exception as e:
            body = json.dumps({"error": str(e)}, ensure_ascii=False).encode("utf-8")
            self.send_response(502)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Cache-Control", "no-store, max-age=0")
            self.end_headers()
            self.wfile.write(body)
