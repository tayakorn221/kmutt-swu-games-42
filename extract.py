# -*- coding: utf-8 -*-
"""ดึงข้อมูลทีม มจธ. จาก bat.tournamentsoftware.com -> kmutt_data.json
รันซ้ำได้เรื่อยๆ (ข้อมูล schedule). ผลแพ้ชนะ/สกอร์จะอัปเดตอัตโนมัติเมื่อระบบกรอก.

ใส่ --fresh เพื่อบังคับโหลดใหม่ (ไม่ใช้ cache).
logic ขูดจริงอยู่ใน scraper.py (ใช้ร่วมกับ Vercel serverless)."""
import sys, json
from scraper import scrape

USE_CACHE = ("--fresh" not in sys.argv)

out = scrape(use_cache=USE_CACHE, log=print)

with open("kmutt_data.json", "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, indent=2)

print(f"\nเสร็จ! แมตช์ มจธ. ทั้งหมด: {len(out['matches'])}")
print(f"club_id -> uni: {out['club_uni']}")
print("บันทึก kmutt_data.json")
