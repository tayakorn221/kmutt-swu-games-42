# -*- coding: utf-8 -*-
"""สร้างไฟล์สำหรับเว็บไซต์:
- kmutt_sheet.csv : ตารางแบนสำหรับ import เข้า Google Sheets (แก้คอลัมน์ ผล/สกอร์ ได้)
- data.js         : ข้อมูล fallback ฝังในเว็บ (เปิดออฟไลน์ได้)
"""
import json, csv, io

d = json.load(open("kmutt_data.json", encoding="utf-8"))

DOW = {0:"จ.",1:"อ.",2:"พ.",3:"พฤ.",4:"ศ.",5:"ส.",6:"อา."}
THMON = ""

def flat_rows():
    rows = []
    for m in d["matches"]:
        kp = [p["name"] for p in m["kmutt_players"]]
        kp += [""] * (2 - len(kp))
        opp = [o["name"] for o in m["opponents"] if o["name"] != "Bye"]
        opp += [""] * (2 - len(opp))
        ou = ", ".join(sorted(set(o["uni"] for o in m["opponents"] if o["uni"])))
        th = m["datetime"]["th"]
        iso = m["datetime"]["iso"]
        date_th = th.rsplit(" ", 1)[0] if " " in th else th   # "อา. 31/5/2569"
        time_ = th.rsplit(" ", 1)[1] if " " in th and ":" in th.rsplit(" ",1)[1] else ""
        result = m["result"]
        rows.append([
            m["match_id"], date_th, time_, iso[:10], m["court"],
            m["event"], m["round"], kp[0], kp[1], opp[0], opp[1], ou,
            result, m["score"],
        ])
    return rows

HEAD = ["รหัสแมตช์","วันที่","เวลา","วันที่ISO","คอร์ท","ประเภท","รอบ",
        "คู่ มจธ. 1","คู่ มจธ. 2","คู่แข่ง 1","คู่แข่ง 2","สังกัดคู่แข่ง",
        "ผล","สกอร์"]

rows = flat_rows()

# CSV (UTF-8 BOM ให้ Google Sheets/Excel อ่านไทยได้)
with open("kmutt_sheet.csv", "w", encoding="utf-8-sig", newline="") as f:
    w = csv.writer(f)
    w.writerow(HEAD)
    w.writerows(rows)

# data.js — โครงสร้างเดียวกับที่เว็บใช้
web = {"tournament": d["tournament"], "venue": "อาคารกีฬา 2 มศว องครักษ์",
       "matches": []}
for m in d["matches"]:
    web["matches"].append({
        "id": m["match_id"],
        "event": m["event"], "round": m["round"],
        "th": m["datetime"]["th"], "iso": m["datetime"]["iso"],
        "court": m["court"],
        "kmutt": [p["name"] for p in m["kmutt_players"]],
        "opp": [{"name": o["name"], "uni": o["uni"]} for o in m["opponents"]],
        "result": m["result"], "score": m["score"], "tbd": m.get("tbd", False),
    })
with open("data.js", "w", encoding="utf-8") as f:
    f.write("window.KMUTT_FALLBACK = ")
    json.dump(web, f, ensure_ascii=False, indent=1)
    f.write(";\n")

print("สร้าง kmutt_sheet.csv (%d แถว) และ data.js แล้ว" % len(rows))
