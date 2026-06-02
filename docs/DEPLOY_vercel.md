# Deploy ขึ้น Vercel (ปุ่มดึงข้อมูลสดในเว็บ)

> ✅ **LIVE แล้ว:** https://kmutt-swu-games-42-6cmb.vercel.app/
> `/api/matches` ขูดสดจาก tournamentsoftware (รวมสกอร์รายเซ็ต)
> ตั้งค่าใช้ `builds`/`routes` ใน `vercel.json` (ไม่ใช่ zero-config — ดูหมายเหตุท้ายไฟล์)

เว็บนี้ทำงานได้ 2 ที่:
- **Vercel** (หลัก): มี `/api/matches` ขูดข้อมูลสดจาก tournamentsoftware (รวมสกอร์รายเซ็ต)
- **โฮสต์สแตติก** (GitHub Pages ฯลฯ): ไม่มี `/api` จะใช้ `data.js` (สแนปช็อตตอนอัปโหลด)

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
สกอร์รายเซ็ต (เช่น `21-15, 19-21, 21-10`) ดึงสดจาก tournamentsoftware เองอัตโนมัติ
— ไม่ต้องกรอกเอง · ขึ้นตามที่ระบบกลางลงผลให้

## ถ้าอยากใช้ URL เดิม (github.io)
github.io ยังเปิดได้ แต่ไม่มี `/api` จึงโชว์ข้อมูลใน `data.js` (สแนปช็อต ไม่ดึงสด)
ถ้าต้องการให้ github.io ดึงสดด้วย ต้องชี้ไปที่ `/api` ของ Vercel (cross-origin) — ค่อยทำเพิ่มได้
