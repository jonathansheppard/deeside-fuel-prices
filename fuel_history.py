"""Deeside fuel widget: writes history.json, the cheapest local petrol and diesel price
for each of the last 30 complete days, rebuilt from the git snapshots of stations.json.
Same rules as fuel-widget.html: Flintshire stations only (postcode checked against postcodes.io),
no Costco, price under 5 days old, 115p floor. Also publishes the Flintshire postcode list the widget uses.
One-day jumps of 10p or more are smoothed out (bad data, e.g. 27 Oct 2026).
Run daily from cron; update-api.py commits history.json with its next push."""
import json, os, subprocess, urllib.request, datetime as dt

REPO = os.path.expanduser("~/deeside-fuel-prices")
STALE_H, DAYS, MIN_STATIONS = 120, 29, 10  # skip days with too few Flintshire stations reporting

def flintshire_postcodes():
    st = json.load(open(os.path.join(REPO, "stations.json")))["stations"]
    pcs = sorted({(s.get("postcode") or "").strip().upper() for s in st if s.get("postcode")})
    out = set()
    for i in range(0, len(pcs), 100):
        req = urllib.request.Request("https://api.postcodes.io/postcodes", data=json.dumps({"postcodes": pcs[i:i + 100]}).encode(),
                                     headers={"Content-Type": "application/json"})
        for r in json.load(urllib.request.urlopen(req, timeout=30))["result"]:
            if (r["result"] or {}).get("admin_district") == "Flintshire": out.add(r["query"])
    return out

FLINT = flintshire_postcodes()

def pick(data):
    t0 = dt.datetime.fromisoformat(data["lastUpdated"].replace("Z", "+00:00"))
    def fresh(s):
        if not s.get("updated"): return False
        u = dt.datetime.fromisoformat(s["updated"].replace("Z", "+00:00"))
        return (t0 - u).total_seconds() / 3600 < STALE_H
    ok = [s for s in data["stations"] if "COSTCO" not in (s.get("name") or "").upper()
          and (s.get("postcode") or "").strip().upper() in FLINT and fresh(s)]
    if len(ok) < MIN_STATIONS: return None, None
    u = min([s["unleaded"] for s in ok if (s.get("unleaded") or 0) >= 115], default=None)
    d = min([s["diesel"] for s in ok if (s.get("diesel") or 0) >= 115], default=None)
    return u, d

def clean(v):
    out = list(v)
    for i in range(1, len(v) - 1):
        if None in (v[i - 1], v[i], v[i + 1]): continue
        if abs(v[i] - v[i - 1]) >= 10 and abs(v[i] - v[i + 1]) >= 10:
            out[i] = round((v[i - 1] + v[i + 1]) / 2, 1)
    return out

today = dt.date.today()
rows = []
for k in range(DAYS, 0, -1):
    day = today - dt.timedelta(days=k)
    end = (day + dt.timedelta(days=1)).isoformat() + " 00:00"
    c = subprocess.run(["git", "-C", REPO, "log", "-1", "--format=%H", f"--before={end}", "--", "stations.json"],
                       capture_output=True, text=True).stdout.strip()
    if not c: continue
    try:
        u, d = pick(json.loads(subprocess.run(["git", "-C", REPO, "show", f"{c}:stations.json"],
                                              capture_output=True, text=True).stdout))
    except Exception as e:
        print("skip", day, e); continue
    if u is None or d is None: continue
    rows.append([day.isoformat(), u, d])
u, d = clean([r[1] for r in rows]), clean([r[2] for r in rows])
out = {"updated": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"), "flintshire": sorted(FLINT),
       "days": [{"date": r[0], "unleaded": u[i], "diesel": d[i]} for i, r in enumerate(rows)]}
tmp = os.path.join(REPO, "history.json.tmp")
json.dump(out, open(tmp, "w"))
os.replace(tmp, os.path.join(REPO, "history.json"))
print(dt.datetime.now().strftime("%Y-%m-%d %H:%M"), "history.json:", len(rows), "days")
