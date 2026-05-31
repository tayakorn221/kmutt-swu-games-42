# -*- coding: utf-8 -*-
"""Logic ขูดข้อมูลทีม มจธ. จาก bat.tournamentsoftware.com.

ใช้ร่วมกันระหว่าง:
  - extract.py        (CLI: เขียน kmutt_data.json)
  - api/matches.py    (Vercel serverless: ส่ง JSON ให้เว็บ)

จุดสำคัญ: ฟังก์ชัน scrape() ดึงหน้าโปรไฟล์ผู้เล่น มจธ. แบบ "ยิงขนาน"
(ThreadPoolExecutor) เพื่อให้เร็วพอสำหรับ serverless (~5 วิ แทน ~40 วิ)."""

import re, html, json, os, time, hashlib, shutil, subprocess, urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed

TID = "08e7fe57-56e4-47f9-b072-54c28ca55d56"
BASE = "https://bat.tournamentsoftware.com"
HDR = {"User-Agent": "Mozilla/5.0", "X-Requested-With": "XMLHttpRequest"}


def _curl(url, post=False):
    if not shutil.which("curl"):
        return ""
    cmd = ["curl", "-s", "-L", url, "-H", "User-Agent: Mozilla/5.0",
           "-H", "X-Requested-With: XMLHttpRequest"]
    if post:
        cmd += ["-X", "POST", "-H", "Content-Length: 0", "--data", ""]
    return subprocess.run(cmd, capture_output=True).stdout.decode("utf-8", "replace")


def _urllib(url, post=False):
    req = urllib.request.Request(url, headers=HDR, method="POST" if post else "GET")
    if post:
        req.data = b""
    return urllib.request.urlopen(req, timeout=30).read().decode("utf-8", "replace")


def get(url, post=False, use_cache=False, cache_dir="cache"):
    """ดึง HTML; retry 3 ครั้งด้วย urllib แล้ว fallback ไป curl. cache ลงดิสก์เมื่อ use_cache."""
    cf = None
    if use_cache:
        cf = os.path.join(cache_dir, hashlib.md5(
            (("P:" if post else "G:") + url).encode()).hexdigest() + ".html")
        if os.path.exists(cf) and os.path.getsize(cf) > 500:
            return open(cf, encoding="utf-8").read()
    last = None
    for _ in range(3):
        try:
            txt = _urllib(url, post)
            if len(txt) > 500:
                if cf:
                    os.makedirs(cache_dir, exist_ok=True)
                    open(cf, "w", encoding="utf-8").write(txt)
                return txt
        except Exception as e:
            last = e
            time.sleep(2)
    txt = _curl(url, post)
    if len(txt) > 500:
        if cf:
            os.makedirs(cache_dir, exist_ok=True)
            open(cf, "w", encoding="utf-8").write(txt)
        return txt
    raise RuntimeError(f"fetch failed: {url} ({last})")


def clean(s):
    return re.sub(r"\s+", " ", html.unescape(re.sub("<[^>]+>", "", s))).strip()


_PLAYER_PAT = re.compile(
    r'player=(\d+)"[^>]*>\s*<span class="nav-link__value">(.*?)</span>.*?'
    r'media__content-subinfo.*?<span class="nav-link__value">(.*?)</span>', re.S)


def parse_players(pc):
    """HTML ของ GetPlayersContent -> {pid: {name, uni}}"""
    players = {}
    for m in _PLAYER_PAT.finditer(pc):
        players[m.group(1)] = {
            "name": clean(m.group(2)).rstrip(",").strip(),
            "uni": clean(m.group(3)),
        }
    return players


def parse_player_page(data, matches, club_of):
    """แยกแมตช์จากหน้าโปรไฟล์ผู้เล่น 1 คน -> เติมลง matches/club_of (in-place)."""
    items = re.split(r'<li class="match-group__item">', data)[1:]
    if not items:
        return
    for it in items:
        header = it.split('<div class="match__body"')[0]
        body = ""
        bm = re.search(r'<div class="match__body".*?(?=<div class="match__result"|<div class="match__footer"|$)', it, re.S)
        if bm:
            body = bm.group(0)
        footer = ""
        fm = re.search(r'<div class="match__footer".*', it, re.S)
        if fm:
            footer = fm.group(0)
        round_ = ""; event = ""; draw_id = ""
        ev = re.search(r'draw=(\d+)[^>]*>\s*<span class="nav-link__value">(.*?)</span>', header)
        if ev:
            draw_id = ev.group(1); event = clean(ev.group(2))
        rd = re.search(r'<span title="([^"]*)" class="nav-link">\s*<span class="nav-link__value">', header)
        if rd:
            round_ = clean(rd.group(1))
        rows = re.split(r'<div class="match__row ', body)[1:]
        sides = []
        for r in rows:
            won = r.startswith('has-won')
            status = ""
            st = re.search(r'match__status">([^<]*)</span>', r)
            if st:
                status = clean(st.group(1))
            pls = []
            for pm in re.finditer(r'data-player-id="(\d+)" data-club-id="(\d*)"[^>]*>\s*<span class="nav-link__value">(.*?)</span>', r):
                pid, cid, nm = pm.group(1), pm.group(2), clean(pm.group(3))
                pls.append({"id": pid, "club": cid, "name": nm})
                if cid:
                    club_of[pid] = cid
            is_bye_text = bool(re.search(r'nav-link__value">\s*Bye\s*</span>', r))
            sides.append({"players": pls, "won": won, "status": status,
                          "bye": is_bye_text, "empty": (not pls and not is_bye_text)})
        dt = ""; court = ""; mid = ""
        cm = re.search(r'matchcalendarhandler\.ashx\?code=[^&]+&(?:amp;)?id=(\d+)', it)
        if cm:
            mid = cm.group(1)
        dm = re.search(r'<span class="nav-link__value">\s*([^<]*\d{1,2}/\d{1,2}/\d{4}[^<]*)</span>', footer)
        if dm:
            dt = clean(dm.group(1))
        cc = re.search(r'icon-marker[^>]*>.*?<span class="nav-link__value">(.*?)</span>', footer, re.S)
        if cc:
            court = clean(cc.group(1))
        allids = sorted([p["id"] for s in sides for p in s["players"]])
        key = f"d{draw_id}-" + "_".join(allids) if allids else (mid or f"x{len(matches)}")
        if mid:
            key = "m" + mid
        if key in matches:
            continue
        matches[key] = {
            "match_id": mid, "draw_id": draw_id, "event": event,
            "round": round_, "datetime": dt, "court": court, "sides": sides,
        }


def conv_date(s):
    """แปลงวันที่ พ.ศ. -> ISO ค.ศ. (เก็บทั้ง th ดิบและ iso). เติม 0 หน้าชั่วโมงให้เรียงถูก."""
    m = re.search(r'(\d{1,2})/(\d{1,2})/(\d{4})\s*(\d{1,2}:\d{2})?', s)
    if not m:
        return {"th": s, "iso": ""}
    d, mo, y, t = m.group(1), m.group(2), int(m.group(3)), m.group(4) or ""
    if t:
        hh, mm = t.split(":")
        t = f"{int(hh):02d}:{mm}"
    ce = y - 543
    iso = f"{ce:04d}-{int(mo):02d}-{int(d):02d}" + (f" {t}" if t else "")
    return {"th": s.strip(), "iso": iso}


def _parse_points(result_html):
    """<div class='match__result'> ... </div> -> (games_side0, games_side1)
    แต่ละ <ul class='points'> = 1 เกม มี 2 <li> (ฝั่งบน, ฝั่งล่าง) เรียงตาม match__row."""
    s0, s1 = [], []
    for ul in re.findall(r'<ul class="points">(.*?)</ul>', result_html, re.S):
        cells = re.findall(r'<li class="points__cell[^"]*">\s*(\d+)\s*</li>', ul)
        if len(cells) >= 2:
            s0.append(int(cells[0])); s1.append(int(cells[1]))
    return s0, s1


def parse_scores_page(html, out_map):
    """หน้า Matches/MatchesInDay -> เติม out_map[frozenset(all ids)] =
    {"sides": [(side_ids, [games]), ...], "winner": frozenset|None} (in-place).
    ข้ามแมตช์ที่ยังไม่มีผล (ไม่มี points__cell). row ที่ขึ้นต้น 'has-won' = ฝั่งชนะ."""
    for it in re.split(r'<li class="match-group__item">', html)[1:]:
        rm = re.search(r'<div class="match__result">(.*?)</div>', it, re.S)
        if not rm or 'points__cell' not in rm.group(1):
            continue
        s0, s1 = _parse_points(rm.group(1))
        if not s0:
            continue
        rows = re.split(r'<div class="match__row ', it[:rm.start()])[1:]
        if len(rows) < 2:
            continue
        s0_ids = frozenset(re.findall(r'data-player-id="(\d+)"', rows[0]))
        s1_ids = frozenset(re.findall(r'data-player-id="(\d+)"', rows[1]))
        all_ids = s0_ids | s1_ids
        if not all_ids:
            continue
        winner = s0_ids if rows[0].startswith('has-won') else (
            s1_ids if rows[1].startswith('has-won') else None)
        out_map[all_ids] = {"sides": [(s0_ids, s0), (s1_ids, s1)], "winner": winner}


def scrape_scores(use_cache=False, max_workers=8, log=lambda *a: None):
    """ดึงสกอร์จากหน้า Matches ของทัวร์ (ทุกวันแข่ง — หน้านี้มีคอลัมน์ points ที่หน้าโปรไฟล์ผู้เล่นไม่มี).
    คืน {frozenset(all_ids): {"sides": [(side_ids, [games]), ...], "winner": frozenset|None}}.
    พลาด = คืน {} (ไม่ทำให้ทั้ง scrape ล้ม)."""
    score_map = {}
    try:
        idx = get(f"{BASE}/tournament/{TID}/Matches", use_cache=use_cache)
    except Exception as e:
        log(f"  ! ดึงหน้า Matches ไม่ได้: {e}")
        return score_map
    parse_scores_page(idx, score_map)  # หน้าแรก = สกอร์ของวันแรกอยู่แล้ว
    dates = sorted(set(re.findall(r'MatchesInDay\?date=(\d+)', idx)))
    urls = [f"{BASE}/tournament/{TID}/Matches/MatchesInDay?date={d}" for d in dates]
    if urls:
        with ThreadPoolExecutor(max_workers=max_workers) as ex:
            futs = {ex.submit(get, u, False, use_cache): u for u in urls}
            for f in as_completed(futs):
                try:
                    parse_scores_page(f.result(), score_map)
                except Exception as e:
                    log(f"    ! score page error {futs[f]}: {e}")
    return score_map


def _score_for(kmutt_side, opp_side, score_map):
    """สกอร์รายเกมของแมตช์ (มุม มจธ.) -> 'มจธ.-คู่แข่ง' ต่อเกม เช่น '21-12, 23-21'. ไม่เจอ = ''."""
    if not opp_side or not opp_side.get("players"):
        return ""
    kids = frozenset(p["id"] for p in kmutt_side["players"])
    oids = frozenset(p["id"] for p in opp_side["players"])
    entry = score_map.get(kids | oids)
    if not entry:
        return ""
    kg = og = None
    for sid, games in entry["sides"]:
        if sid == kids:
            kg = games
        elif sid == oids:
            og = games
    if kg is None or og is None or len(kg) != len(og):
        return ""
    # sanity check: ฝั่งที่ชนะเกมมากกว่า (จาก kg/og) ต้องตรงกับ winner (จากธง has-won)
    # ไม่ตรง = markup ต้นทางสลับลำดับ <li> คะแนนกับ row ผู้เล่น -> สกอร์สลับข้าง ทิ้งไปไม่แสดงผิด
    winner = entry.get("winner")
    if winner in (kids, oids):
        kw = sum(a > b for a, b in zip(kg, og))
        ow = sum(a < b for a, b in zip(kg, og))
        if (kids if kw > ow else oids) != winner:
            return ""
    return ", ".join(f"{a}-{b}" for a, b in zip(kg, og))


def _result_for(kmutt_side, opp_side, score_map):
    """ผลแพ้/ชนะจากหน้า Matches (อัปเดตเร็วกว่า has-won หน้าโปรไฟล์). ไม่รู้ผล = ''."""
    if not opp_side or not opp_side.get("players"):
        return ""
    kids = frozenset(p["id"] for p in kmutt_side["players"])
    oids = frozenset(p["id"] for p in opp_side["players"])
    entry = score_map.get(kids | oids)
    if not entry or not entry.get("winner"):
        return ""
    return "ชนะ" if entry["winner"] == kids else "แพ้"


def scrape(use_cache=False, max_workers=24, log=lambda *a: None):
    """ขูดทั้งหมด -> dict โครงสร้างเดียวกับ kmutt_data.json."""
    log("ดึงรายชื่อผู้เล่นทั้งหมด...")
    pc = get(f"{BASE}/tournament/{TID}/Players/GetPlayersContent", post=True, use_cache=use_cache)
    players = parse_players(pc)
    log(f"  ผู้เล่นทั้งหมด: {len(players)}")

    KMUTT = [pid for pid, v in players.items() if "มจธ" in v["uni"]]
    log(f"  ผู้เล่น มจธ.: {len(KMUTT)}")

    # ยิงขนานดึงหน้าโปรไฟล์ มจธ. ทุกคน
    htmls = {}
    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        futs = {ex.submit(get, f"{BASE}/sport/player.aspx?id={TID}&player={pid}", False, use_cache): pid
                for pid in KMUTT}
        for f in as_completed(futs):
            pid = futs[f]
            try:
                htmls[pid] = f.result()
            except Exception as e:
                log(f"    ! error player={pid}: {e}")

    # parse แบบลำดับ (กัน race บน dict ที่แชร์กัน) — ลำดับตาม KMUTT เพื่อความนิ่ง
    club_of = {}
    matches = {}
    for pid in KMUTT:
        if pid in htmls:
            parse_player_page(htmls[pid], matches, club_of)

    # club_id -> ชื่อมหาวิทยาลัย
    club_uni = {}
    tmp = {}
    for pid, cid in club_of.items():
        if pid in players:
            tmp.setdefault(cid, {}).setdefault(players[pid]["uni"], 0)
            tmp[cid][players[pid]["uni"]] += 1
    for cid, dd in tmp.items():
        club_uni[cid] = max(dd, key=dd.get)

    def uni_of(p):
        if p["id"] in players:
            return players[p["id"]]["uni"]
        return club_uni.get(p["club"], "")

    out = {"tournament": "กีฬาบุคลากรมหาวิทยาลัยแห่งประเทศไทย ครั้งที่ 42 มศว เกมส์",
           "sport": "แบดมินตัน", "club_uni": club_uni, "players": [], "matches": []}
    for pid in KMUTT:
        out["players"].append({"id": pid, "name": players[pid]["name"], "uni": players[pid]["uni"]})

    log("ดึงสกอร์จากหน้า Matches...")
    score_map = scrape_scores(use_cache=use_cache, max_workers=max_workers, log=log)
    log(f"  แมตช์ที่มีสกอร์: {len(score_map)}")

    KSET = set(KMUTT)
    for k, mt in matches.items():
        sides = mt["sides"]
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
        rec["tbd"] = False
        if opp_side and opp_side.get("players"):
            rec["opponents"] = [{"name": p["name"], "uni": uni_of(p), "id": p["id"]} for p in opp_side["players"]]
            if kmutt_side["won"]:
                rec["result"] = "ชนะ"
            elif opp_side.get("won"):
                rec["result"] = "แพ้"
            else:
                # หน้าโปรไฟล์ยังไม่ลงผล -> เดาจากหน้า Matches (has-won) ที่อัปเดตเร็วกว่า
                rec["result"] = _result_for(kmutt_side, opp_side, score_map)
        elif opp_side and opp_side.get("bye"):
            rec["opponents"] = [{"name": "Bye", "uni": "", "id": ""}]
            rec["result"] = "บาย"
        else:
            rec["opponents"] = [{"name": "รอคู่แข่ง", "uni": "", "id": ""}]
            rec["tbd"] = True
            rec["result"] = ""
        rec["score"] = _score_for(kmutt_side, opp_side, score_map)
        out["matches"].append(rec)

    # จัด "บาย" เข้าวัน ตามวันของแมตช์จริงของคู่เดิม+ประเภทเดิม
    dated_day = {}
    for m in out["matches"]:
        if m["datetime"]["iso"] and m["result"] != "บาย":
            key = (m["event"], frozenset(p["name"] for p in m["kmutt_players"]))
            iso = m["datetime"]["iso"][:10]
            th = m["datetime"]["th"].rsplit(" ", 1)[0] if " " in m["datetime"]["th"] else m["datetime"]["th"]
            if key not in dated_day or iso < dated_day[key][0]:
                dated_day[key] = (iso, th)
    for m in out["matches"]:
        if m["result"] == "บาย" and not m["datetime"]["iso"]:
            key = (m["event"], frozenset(p["name"] for p in m["kmutt_players"]))
            if key in dated_day:
                m["datetime"]["iso"] = dated_day[key][0]
                m["datetime"]["th"] = dated_day[key][1]
                m["bye_day_inferred"] = True

    def _skey(r):
        iso = r["datetime"]["iso"]
        date = iso[:10] if len(iso) >= 10 else "9999-99-99"
        tt = iso[11:16] if len(iso) >= 16 else "99:99"
        return (date, tt, r["event"], r["round"])
    out["matches"].sort(key=_skey)
    return out


def to_web(data, scores=None):
    """แปลง dict จาก scrape() -> โครงสร้างที่เว็บใช้ (เหมือน data.js / KMUTT_FALLBACK).
    scores: {match_id: score} เพื่อ merge สกอร์ที่ผู้ใช้กรอกเองในชีต."""
    scores = scores or {}
    web = {"tournament": data["tournament"], "venue": "อาคารกีฬา 2 มศว องครักษ์", "matches": []}
    for m in data["matches"]:
        mid = m["match_id"]
        web["matches"].append({
            "id": mid,
            "event": m["event"], "round": m["round"],
            "th": m["datetime"]["th"], "iso": m["datetime"]["iso"],
            "court": m["court"],
            "kmutt": [p["name"] for p in m["kmutt_players"]],
            "opp": [{"name": o["name"], "uni": o["uni"]} for o in m["opponents"]],
            "result": m["result"],
            "score": (scores.get(mid) or m["score"]) if mid else m["score"],
            "tbd": m.get("tbd", False),
        })
    return web
