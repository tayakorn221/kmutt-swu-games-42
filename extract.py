# -*- coding: utf-8 -*-
"""ดึงข้อมูลทีม มจธ. จาก bat.tournamentsoftware.com -> kmutt_data.json
รันซ้ำได้เรื่อยๆ (ข้อมูล schedule). ผลแพ้ชนะ/สกอร์จะอัปเดตอัตโนมัติเมื่อระบบกรอก."""
import re, html, json, os, time, hashlib, subprocess, urllib.request

TID = "08e7fe57-56e4-47f9-b072-54c28ca55d56"
BASE = "https://bat.tournamentsoftware.com"
HDR = {"User-Agent": "Mozilla/5.0", "X-Requested-With": "XMLHttpRequest"}
CACHE = "cache"
USE_CACHE = ("--fresh" not in os.sys.argv)  # ใส่ --fresh เพื่อบังคับโหลดใหม่
os.makedirs(CACHE, exist_ok=True)

def _curl(url, post=False):
    cmd = ["curl", "-s", "-L", url, "-H", "User-Agent: Mozilla/5.0",
           "-H", "X-Requested-With: XMLHttpRequest"]
    if post:
        cmd += ["-X", "POST", "-H", "Content-Length: 0", "--data", ""]
    return subprocess.run(cmd, capture_output=True).stdout.decode("utf-8", "replace")

def get(url, post=False):
    cf = os.path.join(CACHE, hashlib.md5((("P:" if post else "G:") + url).encode()).hexdigest() + ".html")
    if USE_CACHE and os.path.exists(cf) and os.path.getsize(cf) > 500:
        return open(cf, encoding="utf-8").read()
    last = None
    for attempt in range(3):
        try:
            req = urllib.request.Request(url, headers=HDR, method="POST" if post else "GET")
            if post:
                req.data = b""
            txt = urllib.request.urlopen(req, timeout=30).read().decode("utf-8", "replace")
            if len(txt) > 500:
                open(cf, "w", encoding="utf-8").write(txt)
                return txt
        except Exception as e:
            last = e
            time.sleep(2)
    # fallback: curl
    txt = _curl(url, post)
    if len(txt) > 500:
        open(cf, "w", encoding="utf-8").write(txt)
        return txt
    raise RuntimeError(f"fetch failed: {url} ({last})")

def clean(s):
    return re.sub(r"\s+", " ", html.unescape(re.sub("<[^>]+>", "", s))).strip()

# 1) รายชื่อผู้เล่นทั้งหมด -> id -> (name, uni)
print("ดึงรายชื่อผู้เล่นทั้งหมด...")
pc = get(f"{BASE}/tournament/{TID}/Players/GetPlayersContent", post=True)
players = {}  # pid -> {name, uni}
pat = re.compile(
    r'player=(\d+)"[^>]*>\s*<span class="nav-link__value">(.*?)</span>.*?'
    r'media__content-subinfo.*?<span class="nav-link__value">(.*?)</span>', re.S)
for m in pat.finditer(pc):
    pid = m.group(1)
    players[pid] = {
        "name": clean(m.group(2)).rstrip(",").strip(),
        "uni": clean(m.group(3)),
    }
print(f"  ผู้เล่นทั้งหมด: {len(players)}")

KMUTT = [pid for pid, v in players.items() if "มจธ" in v["uni"]]
print(f"  ผู้เล่น มจธ.: {len(KMUTT)}")

# 2) ดึงหน้าโปรไฟล์ของผู้เล่น มจธ. ทุกคน -> เก็บ club_id ของทุกคนที่เจอ + แมตช์
club_of = {}   # pid -> club_id (เจอจากหน้าแมตช์)
matches = {}   # match_key -> match dict

DOW = {"อา.":"อา","จ.":"จ","อ.":"อ","พ.":"พ","พฤ.":"พฤ","ศ.":"ศ","ส.":"ส"}

def parse_player_page(my_pid, data):
    # แยกทุก match-group__item (ใช้เดลิมิเตอร์เต็ม กันตัดแมตช์แรกหลุด)
    items = re.split(r'<li class="match-group__item">', data)[1:]
    if not items:
        return
    for it in items:
        # แยก sub-block ตามชื่อ class (กัน </li> ซ้อน)
        header = it.split('<div class="match__body"')[0]
        body = ""
        bm = re.search(r'<div class="match__body".*?(?=<div class="match__result"|<div class="match__footer"|$)', it, re.S)
        if bm: body = bm.group(0)
        footer = ""
        fm = re.search(r'<div class="match__footer".*', it, re.S)
        if fm: footer = fm.group(0)
        # round + event (จาก header)
        round_ = ""; event = ""; draw_id = ""
        ev = re.search(r'draw=(\d+)[^>]*>\s*<span class="nav-link__value">(.*?)</span>', header)
        if ev:
            draw_id = ev.group(1); event = clean(ev.group(2))
        rd = re.search(r'<span title="([^"]*)" class="nav-link">\s*<span class="nav-link__value">', header)
        if rd: round_ = clean(rd.group(1))
        # rows (จาก body) — split เฉพาะ match__row จริง (มีช่องว่างตาม) กัน match__row-title-value
        rows = re.split(r'<div class="match__row ', body)[1:]
        sides = []
        for r in rows:
            won = r.startswith('has-won')
            status = ""
            st = re.search(r'match__status">([^<]*)</span>', r)
            if st: status = clean(st.group(1))
            pls = []
            for pm in re.finditer(r'data-player-id="(\d+)" data-club-id="(\d*)"[^>]*>\s*<span class="nav-link__value">(.*?)</span>', r):
                pid, cid, nm = pm.group(1), pm.group(2), clean(pm.group(3))
                pls.append({"id": pid, "club": cid, "name": nm})
                if cid:
                    club_of[pid] = cid
            is_bye = bool(re.search(r'nav-link__value">\s*Bye\s*</span>', r))
            if pls or is_bye:
                sides.append({"players": pls, "won": won, "status": status, "bye": (not pls)})
        # footer: datetime, court, match id
        dt = ""; court = ""; mid = ""
        cm = re.search(r'matchcalendarhandler\.ashx\?code=[^&]+&(?:amp;)?id=(\d+)', it)
        if cm: mid = cm.group(1)
        dm = re.search(r'<span class="nav-link__value">\s*([^<]*\d{1,2}/\d{1,2}/\d{4}[^<]*)</span>', footer)
        if dm: dt = clean(dm.group(1))
        cc = re.search(r'icon-marker[^>]*>.*?<span class="nav-link__value">(.*?)</span>', footer, re.S)
        if cc: court = clean(cc.group(1))
        # key
        allids = sorted([p["id"] for s in sides for p in s["players"]])
        key = f"d{draw_id}-" + "_".join(allids) if allids else (mid or f"x{len(matches)}")
        if mid: key = "m" + mid
        if key in matches:
            continue
        matches[key] = {
            "match_id": mid, "draw_id": draw_id, "event": event,
            "round": round_, "datetime": dt, "court": court, "sides": sides,
        }

for i, pid in enumerate(KMUTT, 1):
    print(f"  [{i}/{len(KMUTT)}] โหลดโปรไฟล์ player={pid} ({players[pid]['name']})")
    try:
        d = get(f"{BASE}/sport/player.aspx?id={TID}&player={pid}")
        parse_player_page(pid, d)
    except Exception as e:
        print("    ! error", e)

# 3) club_id -> ชื่อมหาวิทยาลัย (จาก players list)
club_uni = {}
tmp = {}
for pid, cid in club_of.items():
    if pid in players:
        tmp.setdefault(cid, {}).setdefault(players[pid]["uni"], 0)
        tmp[cid][players[pid]["uni"]] += 1
for cid, d in tmp.items():
    club_uni[cid] = max(d, key=d.get)

# เติม uni ให้ผู้เล่นทุกคนในแมตช์
def uni_of(p):
    if p["id"] in players: return players[p["id"]]["uni"]
    return club_uni.get(p["club"], "")

# 4) แปลงวันที่ พ.ศ. -> ค.ศ. (แสดงทั้งสองแบบ)
def conv_date(s):
    m = re.search(r'(\d{1,2})/(\d{1,2})/(\d{4})\s*(\d{1,2}:\d{2})?', s)
    if not m: return {"th": s, "iso": ""}
    d, mo, y, t = m.group(1), m.group(2), int(m.group(3)), m.group(4) or ""
    if t:  # เติม 0 หน้าชั่วโมง เช่น 9:30 -> 09:30 เพื่อให้เรียงเวลาถูก
        hh, mm = t.split(":")
        t = f"{int(hh):02d}:{mm}"
    ce = y - 543
    iso = f"{ce:04d}-{int(mo):02d}-{int(d):02d}" + (f" {t}" if t else "")
    return {"th": s.strip(), "iso": iso}

out = {"tournament": "กีฬาบุคลากรมหาวิทยาลัยแห่งประเทศไทย ครั้งที่ 42 มศว เกมส์",
       "sport": "แบดมินตัน", "club_uni": club_uni, "players": [], "matches": []}

for pid in KMUTT:
    out["players"].append({"id": pid, "name": players[pid]["name"], "uni": players[pid]["uni"]})

KSET = set(KMUTT)
for k, mt in matches.items():
    sides = mt["sides"]
    # ระบุฝั่ง มจธ.
    rec = {"match_id": mt["match_id"], "event": mt["event"], "round": mt["round"],
           "datetime": conv_date(mt["datetime"]), "court": mt["court"]}
    kmutt_side = None; opp_side = None
    for s in sides:
        if any(p["id"] in KSET for p in s["players"]):
            kmutt_side = s
        else:
            opp_side = s
    if kmutt_side is None:
        continue
    if opp_side is None and len(sides) == 2:
        opp_side = sides[0] if sides[1] is kmutt_side else sides[1]
    rec["kmutt_players"] = [{"name": p["name"], "id": p["id"]} for p in kmutt_side["players"]]
    if opp_side and opp_side.get("players"):
        rec["opponents"] = [{"name": p["name"], "uni": uni_of(p), "id": p["id"]} for p in opp_side["players"]]
    elif opp_side is not None and opp_side.get("bye"):
        rec["opponents"] = [{"name": "Bye", "uni": "", "id": ""}]
    else:
        rec["opponents"] = [{"name": "Bye", "uni": "", "id": ""}]
    # ผล
    is_bye = bool(opp_side and opp_side.get("bye")) or (rec["opponents"] and rec["opponents"][0]["name"] == "Bye")
    if is_bye:
        rec["result"] = "บาย"        # ผ่านเข้ารอบโดยไม่ต้องแข่ง
    elif kmutt_side["won"]:
        rec["result"] = "ชนะ"
    elif opp_side and opp_side.get("won"):
        rec["result"] = "แพ้"
    else:
        rec["result"] = ""           # ยังไม่แข่ง
    rec["score"] = ""  # สกอร์ยังไม่เผยแพร่ — กรอกเองได้
    out["matches"].append(rec)

# sort matches by iso datetime then event
out["matches"].sort(key=lambda r: (r["datetime"]["iso"] or "9999", r["event"], r["round"]))

with open("kmutt_data.json", "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, indent=2)

print(f"\nเสร็จ! แมตช์ มจธ. ทั้งหมด: {len(out['matches'])}")
print(f"club_id -> uni: {club_uni}")
print("บันทึก kmutt_data.json")
