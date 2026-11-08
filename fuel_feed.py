"""Deeside fuel price news feed (8 Nov 2026), for the newsroom reader's Business & Money folder.

Called by update-api.py after each run. Compares stations.json with the last run (fuel_feed_state.json)
and writes feed.xml (served at https://fuel.deeside.com/feed.xml) with items for:
  - a new cheapest unleaded or diesel station in the Deeside area (within 9 miles, not Costco or motorway)
  - a station moving its price by 3p or more since the last run
  - one morning summary a day (area averages against the UK average and last week)
Keeps the newest 60 items."""
import html, json
from datetime import datetime, timezone
from email.utils import format_datetime
from pathlib import Path

DIR = Path(__file__).resolve().parent
STATE = DIR / "fuel_feed_state.json"
OUT = DIR / "feed.xml"
RADIUS = 9
BIG_MOVE = 3.0
MAP = "https://fuel.deeside.com/"
NAMES = {"unleaded": "unleaded", "diesel": "diesel"}


def tidy(name):
    n = (name or "").strip()
    return n.title() if n.isupper() else n


def town(s):
    a = (s.get("address") or "").split(",")
    return a[-1].strip().title() if len(a) > 1 else ""


def area(stations):
    return [s for s in stations if (s.get("distance") or 99) <= RADIUS and not s.get("is_motorway")
            and not s.get("cached") and "COSTCO" not in (s.get("name") or "").upper()]


def item(guid, title, body, when):
    return {"guid": guid, "title": title, "body": body, "date": when}


def build(log=print):
    data = json.loads((DIR / "stations.json").read_text())
    stations = data.get("stations", [])
    now = datetime.now(timezone.utc)
    stamp = now.isoformat(timespec="seconds")
    try:
        state = json.loads(STATE.read_text())
    except Exception:
        state = {}
    items = state.get("items", [])
    seen = {i["guid"] for i in items}
    prev = state.get("prices", {})
    new = []

    near = area(stations)
    for fuel in ("unleaded", "diesel"):
        priced = [s for s in near if s.get(fuel)]
        if not priced:
            continue
        best = min(priced, key=lambda s: s[fuel])
        key = f"cheapest-{fuel}-{best.get('node_id') or best['name']}-{best[fuel]}"
        last = state.get("cheapest", {}).get(fuel)
        if last and last != key and key not in seen:
            nm = tidy(best["name"])
            t = town(best)
            new.append(item(key, f"Cheapest {fuel} in Deeside is now {nm}{', ' + t if t else ''} at {best[fuel]:.1f}p",
                            f"{nm} is now the cheapest place for {fuel} within {RADIUS} miles of Queensferry, at {best[fuel]:.1f}p a litre "
                            f"(Costco and motorway services excluded). UK average {data.get('nationalAvg', {}).get(fuel, 0):.1f}p.", stamp))
        state.setdefault("cheapest", {})[fuel] = key

    for s in near:
        sid = s.get("node_id") or s["name"]
        for fuel in ("unleaded", "diesel"):
            p, q = s.get(fuel), prev.get(f"{sid}|{fuel}")
            if p and q and abs(p - q) >= BIG_MOVE:
                d = p - q
                nm = tidy(s["name"])
                t = town(s)
                guid = f"move-{sid}-{fuel}-{q}-{p}"
                if guid not in seen:
                    new.append(item(guid, f"{nm}{', ' + t if t else ''} {'puts up' if d > 0 else 'cuts'} {fuel} by {abs(d):.1f}p to {p:.1f}p",
                                    f"{nm} has {'raised' if d > 0 else 'cut'} its {fuel} price from {q:.1f}p to {p:.1f}p a litre, "
                                    f"a {'rise' if d > 0 else 'fall'} of {abs(d):.1f}p. It is {s.get('distance')} miles from Queensferry.", stamp))
    state["prices"] = {f"{s.get('node_id') or s['name']}|{f}": s.get(f) for s in near for f in ("unleaded", "diesel") if s.get(f)}

    today = now.strftime("%Y-%m-%d")
    if now.hour >= 7 and state.get("summary_day") != today:
        lines = []
        for fuel in ("unleaded", "diesel"):
            ps = [s[fuel] for s in near if s.get(fuel)]
            wk = [s[f"{fuel}_week"] for s in near if s.get(fuel) and s.get(f"{fuel}_week")]
            if not ps:
                continue
            avg = sum(ps) / len(ps)
            nat = data.get("nationalAvg", {}).get(fuel)
            line = f"{fuel.capitalize()}: Deeside average {avg:.1f}p across {len(ps)} stations"
            if nat:
                line += f", UK average {nat:.1f}p ({'above' if avg > nat else 'below'} by {abs(avg - nat):.1f}p)"
            if wk:
                w = sum(wk) / len(wk)
                line += f"; {'up' if avg > w else 'down'} {abs(avg - w):.1f}p on last week" if abs(avg - w) >= 0.1 else "; same as last week"
            lines.append(line + ".")
        if lines:
            new.append(item(f"summary-{today}", f"Deeside fuel prices today, {now:%-d %B}", " ".join(lines), stamp))
        state["summary_day"] = today

    items = (new + items)[:60]
    state["items"] = items
    STATE.write_text(json.dumps(state, indent=1))
    rss = ['<?xml version="1.0" encoding="UTF-8"?>', '<rss version="2.0"><channel>',
           "<title>Deeside fuel prices</title>", f"<link>{MAP}</link>",
           "<description>Price moves and the cheapest fuel around Deeside, from the GOV.UK Fuel Finder scheme via the Deeside.com fuel map.</description>",
           f"<lastBuildDate>{format_datetime(now)}</lastBuildDate>"]
    for i in items:
        d = datetime.fromisoformat(i["date"])
        rss.append(f"<item><title>{html.escape(i['title'])}</title><link>{MAP}</link>"
                   f"<guid isPermaLink=\"false\">{html.escape(i['guid'])}</guid><pubDate>{format_datetime(d)}</pubDate>"
                   f"<description>{html.escape(i['body'])}</description></item>")
    rss.append("</channel></rss>")
    OUT.write_text("\n".join(rss))
    log(f"Feed: {len(new)} new items, {len(items)} in feed.xml")


if __name__ == "__main__":
    build()
