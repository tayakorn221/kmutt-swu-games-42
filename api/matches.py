# -*- coding: utf-8 -*-
"""Vercel serverless function: GET /api/matches
ขูดข้อมูลสดจาก tournamentsoftware + merge สกอร์จาก Google Sheet -> ส่ง JSON ให้เว็บ.

query ?fresh=1  -> ปิด CDN cache (บังคับดึงสดทันที เมื่อผู้ใช้กดปุ่ม 🔄)
"""
import os, sys, json, csv, io, urllib.request, urllib.parse
from http.server import BaseHTTPRequestHandler

# ให้ import scraper.py (อยู่ที่ root ของ repo) ได้ — Vercel bundle ไฟล์ทั้งโปรเจกต์ให้อยู่แล้ว
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Google Sheet (เก็บคอลัมน์ "สกอร์" ที่ผู้ใช้กรอกเอง) — gviz CSV export
SHEET_ID = "1f6hoUbGWd4_MRB_UQ4Q1e4ET7h9FR2fmcCmv5-KaYI8"
SHEET_CSV = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&gid=0"
COL_MATCH_ID = 0   # รหัสแมตช์
COL_RESULT = 12    # ผล (ชนะ/แพ้/บาย) — ผู้ใช้กรอกเองเพื่อ override ผลที่ scrape มา
COL_SCORE = 13     # สกอร์


def read_sheet():
    """ดึงค่าที่กรอกในชีต -> (scores, results) ทั้งคู่ keyed ด้วย match_id.
    ถ้าพลาด คืน ({}, {}) (ไม่ทำให้ทั้งคำขอล้ม)."""
    scores, results = {}, {}
    try:
        req = urllib.request.Request(SHEET_CSV, headers={"User-Agent": "Mozilla/5.0"})
        raw = urllib.request.urlopen(req, timeout=15).read().decode("utf-8-sig", "replace")
        for r in list(csv.reader(io.StringIO(raw)))[1:]:  # ข้าม header
            if len(r) <= COL_SCORE:
                continue
            mid = (r[COL_MATCH_ID] or "").strip()
            if not mid:
                continue
            sc = (r[COL_SCORE] or "").strip()
            res = (r[COL_RESULT] or "").strip()
            if sc:
                scores[mid] = sc
            if res:
                results[mid] = res
    except Exception:
        pass
    return scores, results


def build_payload():
    from scraper import scrape, to_web  # lazy import (กัน build-time detection ล้ม)
    data = scrape(use_cache=False)
    matches = data.get("matches", [])
    if len(matches) < 10:
        raise RuntimeError(f"scraped too few matches ({len(matches)}) — refusing to serve")
    scores, results = read_sheet()
    web = to_web(data, scores)               # merge สกอร์ที่กรอกในชีต (เหมือนเดิม)
    # ผล (ชนะ/แพ้) ที่กรอกในชีต = override ผลที่ scrape มา (กันกรณีเว็บทางการอัปเดตช้า)
    # เว้นว่างในชีต = ใช้ผลจาก scrape ตามเดิม · บาย/รอคู่แข่งไม่มี match_id จึงไม่ถูกแตะ
    for m in web["matches"]:
        mid = m.get("id")
        if mid and results.get(mid):
            m["result"] = results[mid]
    return web


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
