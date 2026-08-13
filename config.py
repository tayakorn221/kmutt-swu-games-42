# -*- coding: utf-8 -*-
"""ค่าตั้งต้นของ "งาน" กับ "ทีม" ที่ติดตาม — แหล่งเดียวของโปรเจกต์นี้

อยากใช้ระบบนี้กับรายการถัดไป (เช่น ครั้งที่ 43) ให้แก้ไฟล์นี้ไฟล์เดียว แล้วรัน:

    python extract.py --fresh    # ขูดข้อมูลใหม่
    python build_site.py         # สร้าง data.js + CSV
    python build_excel.py        # สร้าง Excel

ไฟล์นี้ถูกอ่านโดย scraper.py / build_site.py / build_excel.py และเว็บ
(ผ่าน meta ที่ build_site.py ฉีดลง data.js)
"""

# ---------- ต้นทางข้อมูล ----------
# TOURNAMENT_ID = ตัวเลข GUID ที่อยู่ใน URL ของทัวร์บน tournamentsoftware
#   เช่น https://bat.tournamentsoftware.com/tournament/08e7fe57-.../  -> เอาส่วนหลัง /tournament/
BASE = "https://bat.tournamentsoftware.com"
TOURNAMENT_ID = "08e7fe57-56e4-47f9-b072-54c28ca55d56"

# ---------- ชื่องาน (ใช้แสดงบนเว็บ/Excel) ----------
TOURNAMENT_NAME = "กีฬาบุคลากรมหาวิทยาลัยแห่งประเทศไทย ครั้งที่ 42 มศว เกมส์"
TOURNAMENT_SHORT = "มศว เกมส์ 42"    # ชื่อสั้น ใช้บน title เบราว์เซอร์/หัวการ์ด
SPORT = "แบดมินตัน"
VENUE = "อาคารกีฬา 2 มศว องครักษ์"

# ---------- ทีมที่ติดตาม ----------
# TEAM_MATCH = คำที่ใช้ค้นในช่อง "สังกัด" ของต้นทางเพื่อคัดนักกีฬาทีมเรา
#   ต้องกว้างพอให้เจอทุกคน แต่แคบพอไม่ให้ปนสถาบันอื่น
#   (มจธ. ใช้ "มจธ" — ไม่ชนกับ มจพ./สจล. ที่เป็นพระจอมเกล้าเหมือนกัน)
TEAM_MATCH = "มจธ"
TEAM_LABEL = "มจธ."          # ชื่อย่อที่โชว์บนเว็บ/หัวคอลัมน์
TEAM_COLOR = "#FF6A1A"       # สี chip ของทีมเราบนการ์ดสรุป

# ---------- การ์ดสรุปลงโซเชียล (summary.html) ----------
SOCIAL_HANDLE = "KMUTT Badminton"
HASHTAG = "#มจธ #มศวเกมส์42"

# ---------- โหมด archive ----------
# True  = แข่งจบแล้ว เว็บอ่านผลจาก data.js อย่างเดียว (ไม่เรียก /api)
# False = กำลังแข่ง เว็บดึงสดจาก /api/matches ทุก 3 นาที + มีปุ่มรีเฟรช
ARCHIVED = True

# ---------- ชื่อไฟล์ผลลัพธ์ ----------
DATA_JSON = "kmutt_data.json"
SHEET_CSV = "kmutt_sheet.csv"
EXCEL_XLSX = "มจธ_มศวเกมส์42.xlsx"


def web_meta():
    """ค่าที่ฉีดลง data.js ให้หน้าเว็บอ่าน (ดูใน build_site.py)"""
    return {
        "tournament": TOURNAMENT_NAME,
        "tournamentShort": TOURNAMENT_SHORT,
        "sport": SPORT,
        "venue": VENUE,
        "team": TEAM_LABEL,
        "teamColor": TEAM_COLOR,
        "social": SOCIAL_HANDLE,
        "hashtag": HASHTAG,
        "archived": ARCHIVED,
    }
