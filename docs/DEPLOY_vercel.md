# Deploy ขึ้น Vercel (ปุ่มดึงข้อมูลสดในเว็บ)

> ✅ **LIVE แล้ว:** https://kmutt-swu-games-42-6cmb.vercel.app/
> `/api/matches` ขูดสดจาก tournamentsoftware + merge สกอร์จาก Google Sheet
> ตั้งค่าใช้ `builds`/`routes` ใน `vercel.json` (ไม่ใช่ zero-config — ดูหมายเหตุท้ายไฟล์)

เว็บนี้ทำงานได้ 2 ที่:
- **GitHub Pages** (เดิม): อ่านข้อมูลจาก Google Sheet — ยังใช้ได้เป็น fallback
- **Vercel** (ใหม่): มี `/api/matches` ขูดข้อมูลสดจาก tournamentsoftware + merge สกอร์จากชีต

## ขั้นตอน deploy (ทำครั้งเดียว ในเบราว์เซอร์)

1. ไป https://vercel.com → **Sign up / Log in ด้วยบัญชี GitHub** (tayakorn221)
2. กด **Add New… → Project**
3. เลือก repo **`kmutt-swu-games-42`** → **Import**
4. หน้า Configure: ปล่อยค่า default ทั้งหมด (Framework = Other, ไม่ต้องตั้ง Build Command)
   - Vercel จะอ่าน `vercel.json` เอง (region สิงคโปร์, ฟังก์ชัน Python)
5. กด **Deploy** → รอ ~1 นาที
6. ได้ URL เช่น `https://kmutt-swu-games-42.vercel.app`

## ตรวจหลัง deploy

- เปิด URL Vercel → แถบสถานะควรขึ้น **"ข้อมูลสดจากต้นทาง · อัปเดต HH:MM"** (จุดเขียว)
- เปิด `https://<your>.vercel.app/api/matches` ตรงๆ → ต้องเห็น JSON (มี `"matches": [...]`)
- กดปุ่ม **🔄** บนเว็บ → ดึงสดทันที (เลี่ยง cache)

> คำขอแรกอาจช้า ~10–15 วิ (ขูดสด + cold start) จากนั้น CDN cache 60 วิ ทำให้คนอื่นเห็นทันที

## เรื่องสกอร์
สกอร์ (แต้ม) ยังกรอกใน Google Sheet เหมือนเดิม — `/api/matches` อ่านมา merge ด้วยรหัสแมตช์
ถ้ามีแมตช์ใหม่ที่ยังไม่มีแถวในชีต ให้เพิ่มแถว (ใส่รหัสแมตช์ + สกอร์) เอง

## ถ้าอยากใช้ URL เดิม (github.io)
github.io ยังเปิดได้และจะ fallback ไปอ่าน Google Sheet (ไม่ได้ขูดสด)
ถ้าต้องการให้ github.io ดึงสดด้วย ต้องชี้ไปที่ `/api` ของ Vercel (cross-origin) — ค่อยทำเพิ่มได้
