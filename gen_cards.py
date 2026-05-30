# -*- coding: utf-8 -*-
"""
Batch auto-gen การ์ดสรุปแมตช์เป็น PNG ด้วย Playwright (optional automation)
ใช้ route/หน้าเดียวกับปุ่ม export ฝั่ง client (summary.html) → ผลลัพธ์ตรงกัน

ติดตั้งครั้งแรก:
    pip install playwright
    python -m playwright install chromium

ใช้งาน:
    python gen_cards.py                         # ทุกวันที่ในข้อมูล, ทั้ง preview + results
    python gen_cards.py 2026-05-31              # เฉพาะวันที่ระบุ
    python gen_cards.py 2026-05-31 preview      # ระบุวัน + โหมด

ไฟล์ออกที่ ./cards/summary-<date>-<mode>.png  (ขนาด 1080x1350 พอดี)
"""
import sys, json, threading, http.server, socketserver, functools, pathlib, time

ROOT = pathlib.Path(__file__).parent.resolve()
OUT = ROOT / "cards"
PORT = 8799

def available_dates():
    s = (ROOT / "data.js").read_text(encoding="utf-8")
    s = s[s.index("{"):].rstrip().rstrip(";")
    return sorted({m["iso"][:10] for m in json.loads(s)["matches"] if m.get("iso")})

def serve():
    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(ROOT))
    httpd = socketserver.TCPServer(("127.0.0.1", PORT), handler)
    httpd.daemon_threads = True
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    return httpd

def main():
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        sys.exit("ต้องติดตั้งก่อน:  pip install playwright && python -m playwright install chromium")

    args = sys.argv[1:]
    dates = [a for a in args if a[:2] == "20"]
    modes = [a for a in args if a in ("preview", "results")] or ["preview", "results"]
    if not dates:
        dates = available_dates()
    OUT.mkdir(exist_ok=True)

    httpd = serve()
    made = []
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            # viewport กว้างกว่า 1080 เพื่อให้ stage ไม่ย่อ (fitStage → scale 1)
            page = browser.new_page(viewport={"width": 1180, "height": 1400}, device_scale_factor=1)
            for d in dates:
                for mode in modes:
                    page.goto(f"http://127.0.0.1:{PORT}/summary.html?date={d}&mode={mode}",
                              wait_until="networkidle")
                    page.wait_for_selector("#card .row, #card .empty", timeout=8000)
                    page.evaluate("document.fonts && document.fonts.ready")
                    page.evaluate("document.getElementById('stage').style.transform='none'")
                    time.sleep(0.3)  # ให้ auto-fit/ฟอนต์ settle
                    out = OUT / f"summary-{d}-{mode}.png"
                    page.locator("#card").screenshot(path=str(out))
                    made.append(out.name)
                    print("✓", out.name)
            browser.close()
    finally:
        httpd.shutdown()
    print(f"\nเสร็จ {len(made)} รูป → {OUT}")

if __name__ == "__main__":
    main()
