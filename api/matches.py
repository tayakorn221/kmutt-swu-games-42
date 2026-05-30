# -*- coding: utf-8 -*-
"""Vercel serverless function: GET /api/matches
ขูดข้อมูลสดจาก tournamentsoftware + merge สกอร์จาก Google Sheet -> ส่ง JSON ให้เว็บ.

query ?fresh=1  -> ปิด CDN cache (บังคับดึงสดทันที เมื่อผู้ใช้กดปุ่ม 🔄)
"""
import os, sys, json, csv, io, urllib.request, urllib.parse
from http.server import BaseHTTPRequestHandler

# ให้ import scraper.py จาก root ของ repo ได้
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scraper import scrape, to_web  # noqa: E402

# Google Sheet (เก็บคอลัมน์ "สกอร์" ที่ผู้ใช้กรอกเอง) — gviz CSV export
SHEET_ID = "1f6hoUbGWd4_MRB_UQ4Q1e4ET7h9FR2fmcCmv5-KaYI8"
SHEET_CSV = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&gid=0"
COL_MATCH_ID = 0   # รหัสแมตช์
COL_SCORE = 13     # สกอร์


def read_scores():
    """ดึงสกอร์ที่กรอกในชีต -> {match_id: score}. ถ้าพลาด คืน {} (ไม่ทำให้ทั้งคำขอล้ม)."""
    try:
        req = urllib.request.Request(SHEET_CSV, headers={"User-Agent": "Mozilla/5.0"})
        raw = urllib.request.urlopen(req, timeout=15).read().decode("utf-8-sig", "replace")
        scores = {}
        rows = list(csv.reader(io.StringIO(raw)))
        for r in rows[1:]:  # ข้าม header
            if len(r) > COL_SCORE:
                mid = (r[COL_MATCH_ID] or "").strip()
                sc = (r[COL_SCORE] or "").strip()
                if mid and sc:
                    scores[mid] = sc
        return scores
    except Exception:
        return {}


def build_payload():
    data = scrape(use_cache=False)
    matches = data.get("matches", [])
    if len(matches) < 10:
        raise RuntimeError(f"scraped too few matches ({len(matches)}) — refusing to serve")
    scores = read_scores()
    return to_web(data, scores)


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
