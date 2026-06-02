# 🏸 KMUTT Badminton Tracker — มศว เกมส์ ครั้งที่ 42

เว็บไซต์ติดตามผลการแข่งขัน **แบดมินตันทีมบุคลากร มจธ. (KMUTT)** ในรายการ
**กีฬาบุคลากรมหาวิทยาลัยแห่งประเทศไทย ครั้งที่ 42 "มศว เกมส์"**
พร้อมชุดสคริปต์ดึงข้อมูล โปรแกรมแข่ง ไฟล์ Excel และเครื่องมือทำการ์ดสรุปลงโซเชียล

> 🌐 **LIVE:** https://kmutt-swu-games-42.vercel.app/
> 📅 31 พ.ค. – 4 มิ.ย. 2569 · 🏟️ อาคารกีฬา 2 มศว องครักษ์ · 🏸 25 นักกีฬา · 22 คู่ · 36 แมตช์

---

## ✨ สิ่งที่เว็บทำได้

- 📊 **สกอร์บอร์ดสด** — นับแมตช์ ชนะ/แพ้/บาย/รอแข่ง อัตโนมัติ
- 🗓️ **แบ่งตามวัน** — โปรแกรมแต่ละวัน เรียงตามเวลา พร้อมคอร์ท
- 🔍 **ค้นหา & กรอง** — ตามชื่อนักกีฬา / คู่แข่ง / มหาวิทยาลัย / ผล
- 🔄 **ปุ่มรีเฟรช (ดึงสดจากต้นทาง)** — กดแล้วเรียก `/api/matches` ขูดข้อมูลล่าสุดจาก tournamentsoftware ทันที โดยไม่ต้องรัน Python (รีเฟรชเองทุก 3 นาทีด้วย)
- 🏸 **สกอร์รายเซ็ตจากต้นทาง** — ดึงสกอร์แต่ละเกมอัตโนมัติ (เช่น 21-15, 19-21, 21-10) ไม่ต้องกรอกเอง
- 🖼️ **ทำการ์ดสรุปลงโซเชียล** — หน้า `summary.html` สร้างการ์ด 1080×1350 (โหมดพรีวิวเช้า / ผลค่ำ · ธีมมืด/สว่าง) ดาวน์โหลดเป็น PNG ได้เลย
- 📱 รองรับมือถือเต็มรูปแบบ · เปิดได้แม้ไม่มีเน็ตต้นทาง (มีข้อมูล fallback ในตัว)

---

## 🧭 ทำงานยังไง (สถาปัตยกรรม)

```
🌐 Vercel:  tournamentsoftware ──ขูดสด──▶ /api/matches ──▶ JSON (CDN cache ~60 วิ)
                                                 │
index.html ── โหลดตามลำดับ ──▶ ① /api/matches (สด) ─▶ ถ้าพลาด ② data.js (ฝังในเว็บ) ──▶ render
                                🔄 ปุ่มรีเฟรช = เรียกด้วย ?fresh=1 (ข้าม cache บังคับขูดใหม่)
```

- **ดึงสดจากต้นทางทั้งหมด:** โปรแกรม · เวลา · คอร์ท · รอบ · คู่แข่ง · ผลแพ้/ชนะ/บาย · **สกอร์รายเซ็ต**
- เว็บไม่เคยขึ้นจอเปล่า — ถ้า `/api` ล่ม จะถอยไป `data.js` (ฝังในเว็บ) อัตโนมัติ
- เปิดไฟล์ในเครื่อง หรือ static host ที่ไม่มี `/api` ก็เปิดได้ — จะใช้ `data.js` แทน

---

## 🛠️ เบื้องหลัง (How it was built)

1. **ดึงข้อมูลจาก tournamentsoftware.com**
   หน้าเว็บโหลดข้อมูลด้วย JavaScript (AJAX) จึงเขียน `scraper.py` เรียก endpoint โดยตรง:
   - รายชื่อผู้เล่นทั้งหมด: `POST /tournament/{id}/Players/GetPlayersContent`
   - แมตช์รายคน: `GET /sport/player.aspx?id={id}&player={n}` (ดึง ~25 หน้า **พร้อมกันด้วย `ThreadPoolExecutor`** — ~5 วิ แทน ~40 วิ เพื่อให้ทันลิมิต serverless)
   - สกอร์รายเซ็ต: ดึงจากหน้า `Matches` ของทัวร์ (มีคอลัมน์คะแนนรายเกม)
   - ระบุสังกัดด้วย `data-club-id` (มจธ. = club-id **7**) แยกจาก มจพ./สจล. ชัดเจน

2. **แปลงข้อมูล** — แตกชื่อนักกีฬา/คู่/คู่แข่ง/มหาวิทยาลัย/วันเวลา (แปลง พ.ศ.→ค.ศ.)/คอร์ท/ผล/สกอร์
   (`scraper.py` มี cache บนดิสก์ + retry + fallback เป็น curl) แล้ว `extract.py` เซฟลง `kmutt_data.json`

3. **🐛 เจอและแก้บั๊กสำคัญ** — parser เดิมตัด *แมตช์แรกของทุกหน้า* ทิ้ง (หาตำแหน่งไปตกกลางแท็ก)
   ทำให้ข้อมูลขาดไป 9 แมตช์ (27 → **36**) แก้โดยใช้เดลิมิเตอร์ `<li class="match-group__item">` เต็ม

4. **✅ ตรวจสอบ 3 ชั้น**
   - ผู้เล่น 25 คน สะกด "มจธ." ตรงกันทุกคน ไม่ปนกับมหา'ลัยพระจอมเกล้าอื่น
   - ทุกหน้าโปรไฟล์: จำนวนที่ parse ได้ = จำนวนจริง (mismatch = 0)
   - Cross-check อิสระ: แมตช์ทั้ง 10 ในหน้า Matches อยู่ในข้อมูลครบ

5. **สร้างผลลัพธ์** — เว็บไซต์ (`index.html`), Excel 3 ชีต, CSV ตารางแบน

6. **🌐 ดึงสดในเว็บผ่าน Vercel** — แยก logic ขูดไปไว้ใน `scraper.py` (ใช้ร่วมกัน) แล้วทำ serverless function
   `api/matches.py` ขูดสด (รวมสกอร์รายเซ็ต) ส่ง JSON ให้เว็บ → ได้ปุ่ม 🔄 โดยผู้ใช้ไม่ต้องรัน Python
   (ดีไซน์เต็มใน [docs/superpowers/specs/2026-05-30-vercel-live-refresh-design.md](docs/superpowers/specs/2026-05-30-vercel-live-refresh-design.md))

7. **🖼️ การ์ดสรุปลงโซเชียล** — `summary.html` เรนเดอร์การ์ด 1080×1350 (สไตล์เพจแบดไทย) แล้ว export
   เป็น PNG ด้วย `html-to-image.js` + ฝังฟอนต์ Bai Jamjuree (`summary-fonts.js`) · ทำเป็นชุดอัตโนมัติได้ด้วย `gen_cards.py`

---

## 📁 โครงสร้างไฟล์

```
หน้าเว็บ
├── index.html            # เว็บไซต์หลัก (ดึงสด /api → data.js)
├── summary.html          # ตัวสร้างการ์ดสรุปลงโซเชียล (1080×1350, PNG)
├── data.js               # ข้อมูล fallback ฝังในเว็บ
├── summary-fonts.js      # ฟอนต์ Bai Jamjuree ฝังในการ์ด (สำหรับ export PNG)
└── html-to-image.js      # ไลบรารีแปลง HTML → PNG (ฝั่ง client)

Vercel (ดึงสด)
├── api/matches.py        # serverless: ขูดสด → JSON (รวมสกอร์รายเซ็ต)
└── vercel.json           # ตั้งค่า build/route + region สิงคโปร์ + รันไทม์ Python

สคริปต์ build (ต้องมี Python)
├── scraper.py            # แกนขูด+parse (ใช้ร่วมกันทั้ง CLI และ Vercel)
├── extract.py            # CLI: scraper → kmutt_data.json
├── build_site.py         # kmutt_data.json → data.js + kmutt_sheet.csv
├── build_excel.py        # kmutt_data.json → ไฟล์ Excel
└── gen_cards.py          # สร้างการ์ด PNG เป็นชุดด้วย Playwright (optional)

ข้อมูล / ผลลัพธ์
├── kmutt_data.json       # ข้อมูลดิบโครงสร้างเต็ม (canonical)
├── kmutt_sheet.csv       # ตารางแบน (CSV) เปิดดู/พิมพ์ได้
├── มจธ_มศวเกมส์42.xlsx    # Excel 3 ชีต: ตารางแมตช์ · นักกีฬา · สรุปผล
└── cache/                # cache HTML ของ scraper (ลบได้ปลอดภัย)

เอกสาร
├── README.md             # ไฟล์นี้
├── README_วิธีใช้.md      # คู่มือผู้ใช้ (ภาษาไทย ละเอียด)
└── docs/                 # คู่มือ deploy Vercel + design spec
```

---

## 🚀 การใช้งาน

**ดูเว็บ:** เปิด https://kmutt-swu-games-42.vercel.app/ — กด **🔄 รีเฟรช** เพื่อดึงผลล่าสุดทันที
(เปิด `index.html` ในเครื่องก็ได้ จะถอยไปอ่าน `data.js` แทน)

**ทำการ์ดลงโซเชียล:** เปิด `summary.html` (หรือกดปุ่ม 🖼️ ในหน้าหลัก) → เลือกวัน + โหมด (พรีวิว/ผล) + ธีม → **⬇ ดาวน์โหลด PNG**
ทำเป็นชุดทุกวันอัตโนมัติ: `pip install playwright && python -m playwright install chromium` แล้ว `python gen_cards.py`

**อัปเดตข้อมูล/ไฟล์ในเครื่อง** (ต้องมี Python):
```bash
python extract.py --fresh   # ขูดข้อมูลล่าสุด → kmutt_data.json
python build_site.py        # สร้าง data.js + kmutt_sheet.csv ใหม่
python build_excel.py       # สร้าง Excel ใหม่
```

**Deploy ขึ้น Vercel:** ดู [docs/DEPLOY_vercel.md](docs/DEPLOY_vercel.md) และ [README_วิธีใช้.md](README_วิธีใช้.md)

---

## 🧰 เทคโนโลยี

- **ดึง/ประมวลผลข้อมูล:** Python (urllib, regex, `ThreadPoolExecutor`, openpyxl)
- **ดึงสดในเว็บ:** Vercel serverless function (Python) + CDN cache
- **เว็บ:** HTML/CSS/JS ล้วน (ไม่มี framework) · ฟอนต์ไทย Bai Jamjuree + Sarabun
- **การ์ดโซเชียล:** html-to-image (export PNG) · Playwright (ทำเป็นชุด, optional)

---

## 📊 แหล่งข้อมูลและข้อจำกัด

ข้อมูลทั้งหมด (โปรแกรม · ผลแพ้/ชนะ · สกอร์รายเซ็ต) ดึงสดจาก [tournamentsoftware.com](https://bat.tournamentsoftware.com/tournament/08E7FE57-56E4-47F9-B072-54C28CA55D56) (ข้อมูลสาธารณะ)
เว็บอัปเดตอัตโนมัติทุก ~3 นาที (มี CDN cache ~60 วิ) — ผล/สกอร์ขึ้นตามที่ระบบกลางลงให้ · ไม่ต้องกรอกเอง

---

## 👤 ผู้จัดทำ

**ออกแบบ & พัฒนาโดย [Tayakorn](https://github.com/tayakorn221)**

📧 [tayakorn2212@gmail.com](mailto:tayakorn2212@gmail.com)  ·  💻 [github.com/tayakorn221](https://github.com/tayakorn221)

---

*ทำเพื่อทีมบุคลากร มจธ. · ไม่เกี่ยวข้องอย่างเป็นทางการกับผู้จัดการแข่งขันหรือ tournamentsoftware.com*
