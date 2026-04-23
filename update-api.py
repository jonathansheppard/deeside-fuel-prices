import requests
import json
import os
import csv
import io
import subprocess
from math import radians, sin, cos, sqrt, atan2
from datetime import datetime, timezone

# ── Credentials ───────────────────────────────────────────────────────────────
CLIENT_ID     = "OXaCtJ25MBEQs0OHobvSf8l3A5ztgsM2"
CLIENT_SECRET = "XMYqgyjvqSjy4MS5BDS6zrKty8nluY29JEOLaXRyXBRHMz6tWmyWTD8Nl7qIeRAE"

BASE_URL      = "https://www.fuel-finder.service.gov.uk"
TOKEN_URL     = f"{BASE_URL}/api/v1/oauth/generate_access_token"
PRICES_URL    = f"{BASE_URL}/api/v1/pfs/fuel-prices"
INFO_URL      = f"{BASE_URL}/api/v1/pfs"

# ── Voluntary retailer feeds ──────────────────────────────────────────────────
RETAILER_FEEDS = [
    {"name": "Tesco",       "url": "https://www.tesco.com/fuel_prices/fuel_prices_data.json"},
    {"name": "Morrisons",   "url": "https://www.morrisons.com/fuel-prices/fuel.json"},
    {"name": "Sainsbury's", "url": "https://api.sainsburys.co.uk/v1/exports/latest/fuel_prices_data.json"},
    {"name": "Asda",        "url": "https://storelocator.asda.com/fuel_prices_data.json"},
    {"name": "MFG",         "url": "https://fuel.motorfuelgroup.com/fuel_prices_data.json"},
    {"name": "Rontec",      "url": "https://www.rontec-servicestations.co.uk/fuel-prices/data/fuel_prices_data.json"},
    {"name": "Jet",         "url": "https://jetlocal.co.uk/fuel_prices_data.json"},
    {"name": "Esso/Tesco",  "url": "https://fuelprices.esso.co.uk/latestdata.json"},
    {"name": "SGN",         "url": "https://www.sgnretail.uk/files/data/SGN_daily_fuel_prices.json"},
]

# ── Google Sheets fallback ────────────────────────────────────────────────────
SHEET_ID      = "1HE-K4RVMbwWOuF6hy-CJg1G5kFWtChpK4w1WKnWqjTQ"
SHEET_GID     = "1435371472"
SHEET_CSV_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={SHEET_GID}"

# ── Output ────────────────────────────────────────────────────────────────────
OUTPUT_FILE   = os.path.expanduser("~/deeside-fuel-prices/stations.json")
REPO_DIR      = os.path.expanduser("~/deeside-fuel-prices")

# ── GitHub token ──────────────────────────────────────────────────────────────
# Set in ~/.zshrc: export GITHUB_TOKEN=your_token_here
GITHUB_TOKEN  = os.environ.get("GITHUB_TOKEN", "")
GITHUB_REMOTE = f"https://{GITHUB_TOKEN}@github.com/jonathansheppard/deeside-fuel-prices.git"

# ── Geographic filter ─────────────────────────────────────────────────────────
LAT_MIN, LAT_MAX = 53.05, 53.45
LNG_MIN, LNG_MAX = -3.45, -2.80

# ── Centre point for distance calculation (Queensferry roundabout) ────────────
CENTRE_LAT = 53.1900
CENTRE_LNG = -3.0333

# ── Price floor ───────────────────────────────────────────────────────────────
PRICE_FLOOR = 115.0

# ── Excluded stations (by postcode) ──────────────────────────────────────────
EXCLUDED_POSTCODES = {
    "LL15 1PE",   # Dyffryn Service Station, Ruthin
    "LL12 8DY",   # Smithy View Acton - unreliable cached prices
}


def log(msg):
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {msg}")


def haversine(lat1, lng1, lat2, lng2):
    R = 3958.8
    lat1, lng1, lat2, lng2 = map(radians, [lat1, lng1, lat2, lng2])
    dlat = lat2 - lat1
    dlng = lng2 - lng1
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlng/2)**2
    return round(R * 2 * atan2(sqrt(a), sqrt(1-a)), 1)


def get_token():
    log("Authenticating with new Fuel Finder API...")
    r = requests.post(TOKEN_URL, json={
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET
    }, timeout=30)
    r.raise_for_status()
    data = r.json()
    token = data.get("data", {}).get("access_token") or data.get("access_token")
    if not token:
        raise ValueError(f"No token in response: {data}")
    log("Token obtained successfully")
    return token


def fetch_all_batches(url, token, extra_params=None):
    headers = {"Authorization": f"Bearer {token}"}
    all_records = []
    batch = 1
    MAX_RETRIES = 3
    while True:
        params = {"batch-number": batch}
        if extra_params:
            params.update(extra_params)
        # Retry loop — API is occasionally slow, don't let one slow batch kill the run
        r = None
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                r = requests.get(url, headers=headers, params=params, timeout=60)
                break
            except (requests.exceptions.ReadTimeout, requests.exceptions.ConnectionError) as e:
                if attempt < MAX_RETRIES:
                    log(f"  Batch {batch} attempt {attempt} timed out, retrying...")
                    continue
                log(f"  Batch {batch} failed after {MAX_RETRIES} attempts: {e}")
                raise
        if r.status_code in (400, 403, 404):
            break
        r.raise_for_status()
        data = r.json()
        if not data:
            break
        all_records.extend(data)
        log(f"  Batch {batch}: {len(data)} items (total: {len(all_records)})")
        batch += 1
    log(f"Total records fetched: {len(all_records)}")
    return all_records


def in_area(lat, lng):
    try:
        return LAT_MIN <= float(lat) <= LAT_MAX and LNG_MIN <= float(lng) <= LNG_MAX
    except (TypeError, ValueError):
        return False


def is_excluded(postcode):
    return (postcode or "").strip().upper() in EXCLUDED_POSTCODES


def valid_price(p):
    try:
        return float(p) >= PRICE_FLOOR
    except (TypeError, ValueError):
        return False


def load_retailer_feeds():
    log("Fetching voluntary retailer feeds...")
    retailer_stations = {}

    for feed in RETAILER_FEEDS:
        try:
            r = requests.get(feed["url"], timeout=15, headers={
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            })
            r.raise_for_status()
            data = r.json()

            stations = data.get("stations", [])
            count = 0
            for s in stations:
                try:
                    lat = float(s.get("location", {}).get("latitude") or s.get("lat") or 0)
                    lng = float(s.get("location", {}).get("longitude") or s.get("lng") or 0)
                except (TypeError, ValueError):
                    continue

                if not in_area(lat, lng):
                    continue

                postcode = (s.get("postcode") or "").strip().upper()
                if not postcode:
                    continue

                if is_excluded(postcode):
                    continue

                prices = s.get("prices", {})
                unleaded = float(prices.get("E10") or prices.get("U") or 0) or None
                diesel   = float(prices.get("B7") or prices.get("D") or 0) or None

                if unleaded and unleaded < PRICE_FLOOR:
                    unleaded = None
                if diesel and diesel < PRICE_FLOOR:
                    diesel = None

                if not unleaded and not diesel:
                    continue

                last_updated = s.get("last_updated") or datetime.now(timezone.utc).isoformat()

                retailer_stations[postcode] = {
                    "name":           s.get("brand", feed["name"]) + " " + s.get("name", "").strip(),
                    "brand":          s.get("brand", feed["name"]),
                    "address":        s.get("address", ""),
                    "postcode":       postcode,
                    "lat":            lat,
                    "lng":            lng,
                    "distance":       haversine(CENTRE_LAT, CENTRE_LNG, lat, lng),
                    "is_supermarket": feed["name"] in ("Tesco", "Morrisons", "Sainsbury's", "Asda"),
                    "is_motorway":    False,
                    "unleaded":       unleaded,
                    "diesel":         diesel,
                    "updated":        last_updated,
                    "cached":         False
                }
                count += 1

            log(f"  {feed['name']}: {count} local stations")

        except Exception as e:
            log(f"  {feed['name']}: failed — {e}")

    log(f"Retailer feeds total: {len(retailer_stations)} local stations")
    return retailer_stations


def load_sheets_fallback():
    log("Loading Google Sheets fallback data...")
    try:
        r = requests.get(SHEET_CSV_URL, timeout=15)
        r.raise_for_status()
        reader = csv.DictReader(io.StringIO(r.text))
        stations = {}
        for row in reader:
            name = row.get("station_name", "").strip()
            if not name:
                continue
            date_str = row.get("date", "")
            if name not in stations:
                stations[name] = row
            else:
                try:
                    d1 = datetime.strptime(date_str, "%m/%d/%Y")
                    d2 = datetime.strptime(stations[name]["date"], "%m/%d/%Y")
                    if d1 > d2:
                        stations[name] = row
                except ValueError:
                    pass
        log(f"Sheets fallback: {len(stations)} stations loaded")
        return stations
    except Exception as e:
        log(f"Sheets fallback failed: {e}")
        return {}


def parse_sheets_date(date_str):
    try:
        dt = datetime.strptime(date_str, "%m/%d/%Y")
        return dt.replace(tzinfo=timezone.utc).isoformat()
    except Exception:
        return date_str


def git_push():
    """Commit and push stations.json to GitHub. Uses os.system for Python 3.14 compatibility."""
    if not GITHUB_TOKEN:
        log("Git: GITHUB_TOKEN not set — skipping push")
        return

    # Stage stations.json
    os.system(f'cd "{REPO_DIR}" && git add stations.json')

    # Check if there's anything to commit
    status = os.popen(f'cd "{REPO_DIR}" && git status --porcelain stations.json').read().strip()
    if not status:
        log("Git: no changes to commit")
        return

    # Commit
    commit_msg = f"Auto-update {datetime.now().strftime('%Y-%m-%d %H:%M')} UTC"
    commit_exit = os.system(f'cd "{REPO_DIR}" && git commit -m "{commit_msg}"')
    if commit_exit != 0:
        log(f"Git: commit failed with exit code {commit_exit}")
        return

    # Pull rebase then push
    pull_exit = os.system(f'cd "{REPO_DIR}" && git pull --rebase {GITHUB_REMOTE} main 2>&1')
    if pull_exit != 0:
        log(f"Git: pull --rebase failed with exit code {pull_exit}")
        return

    push_exit = os.system(f'cd "{REPO_DIR}" && git push {GITHUB_REMOTE} main 2>&1')
    if push_exit == 0:
        log("Git: stations.json pushed to GitHub ✓")
    else:
        log(f"Git: push failed with exit code {push_exit}")


def main():
    log("=" * 50)
    log("Deeside Fuel Prices — API Update")
    log("=" * 50)

    # ── Source 1: New mandatory Fuel Finder API ───────────────────────────────
    token = get_token()

    log("Fetching station info from new API...")
    all_info = fetch_all_batches(INFO_URL, token)

    local_stations = {}
    postcode_index = {}

    for s in all_info:
        loc = s.get("location", {})
        lat = loc.get("latitude")
        lng = loc.get("longitude")
        if not in_area(lat, lng):
            continue
        lat_f = float(lat)
        lng_f = float(lng)
        postcode = (loc.get("postcode") or "").strip().upper()
        if is_excluded(postcode):
            continue
        node_id = s["node_id"]
        local_stations[node_id] = {
            "node_id":        node_id,
            "name":           s.get("trading_name", ""),
            "brand":          s.get("brand_name", s.get("trading_name", "")),
            "address":        loc.get("address", ""),
            "postcode":       postcode,
            "lat":            lat_f,
            "lng":            lng_f,
            "distance":       haversine(CENTRE_LAT, CENTRE_LNG, lat_f, lng_f),
            "is_supermarket": s.get("is_supermarket_service_station", False),
            "is_motorway":    s.get("is_motorway_service_station", False),
            "unleaded":       None,
            "diesel":         None,
            "updated":        None,
            "cached":         False
        }
        if postcode:
            postcode_index[postcode] = node_id

    log(f"Found {len(local_stations)} stations in area from new API")

    log("Fetching fuel prices from new API...")
    all_prices = fetch_all_batches(PRICES_URL, token)

    for p in all_prices:
        node_id = p.get("node_id")
        if node_id not in local_stations:
            continue
        for fp in p.get("fuel_prices", []):
            fuel_type = fp.get("fuel_type", "").upper()
            price     = fp.get("price")
            updated   = fp.get("price_change_effective_timestamp") or fp.get("price_last_updated")
            if not valid_price(price):
                continue
            if "E10" in fuel_type:
                local_stations[node_id]["unleaded"] = float(price)
            elif "B7" in fuel_type or "DIESEL" in fuel_type:
                local_stations[node_id]["diesel"] = float(price)
            if updated:
                local_stations[node_id]["updated"] = updated

    # ── Diagnostic: which stations got no prices from API? ──────────────────
    null_price = [s for s in local_stations.values()
                  if s.get("unleaded") is None and s.get("diesel") is None]
    log(f"DIAGNOSTIC: {len(null_price)} of {len(local_stations)} local stations have NO prices after API match")
    for s in null_price[:20]:
        log(f"  MISSING: {s['name']:<40} | {s['postcode']:<10} | node_id: {s.get('node_id', 'none')}")

    # ── Source 2: Voluntary retailer feeds ───────────────────────────────────
    retailer_data = load_retailer_feeds()

    retailer_added = 0
    retailer_filled = 0
    for postcode, rs in retailer_data.items():
        if postcode in postcode_index:
            node_id = postcode_index[postcode]
            changed = False
            if local_stations[node_id]["unleaded"] is None and rs["unleaded"]:
                local_stations[node_id]["unleaded"] = rs["unleaded"]
                changed = True
            if local_stations[node_id]["diesel"] is None and rs["diesel"]:
                local_stations[node_id]["diesel"] = rs["diesel"]
                changed = True
            if changed:
                local_stations[node_id]["updated"] = rs["updated"]
                retailer_filled += 1
        else:
            local_stations["retailer_" + postcode] = rs
            retailer_added += 1

    log(f"Retailer feeds: {retailer_filled} gaps filled, {retailer_added} new stations added")

    # ── Source 3: Google Sheets fallback ─────────────────────────────────────
    sheets_data = load_sheets_fallback()
    api_names = {s["name"] for s in local_stations.values()}

    fallback_count = 0
    for node_id, station in local_stations.items():
        name = station["name"]
        if name not in sheets_data:
            continue
        row = sheets_data[name]
        changed = False
        if station["unleaded"] is None and valid_price(row.get("unleaded")):
            station["unleaded"] = float(row["unleaded"])
            changed = True
        if station["diesel"] is None and valid_price(row.get("diesel")):
            station["diesel"] = float(row["diesel"])
            changed = True
        if changed:
            station["cached"] = True
            station["updated"] = parse_sheets_date(row.get("date", ""))
            fallback_count += 1

    extra_count = 0
    for name, row in sheets_data.items():
        if name in api_names:
            continue
        unleaded = float(row["unleaded"]) if valid_price(row.get("unleaded")) else None
        diesel   = float(row["diesel"])   if valid_price(row.get("diesel"))   else None
        if not unleaded and not diesel:
            continue
        try:
            lat_f = float(row.get("lat", 0) or 0)
            lng_f = float(row.get("lng", 0) or 0)
        except ValueError:
            lat_f, lng_f = 0.0, 0.0
        local_stations["sheets_" + name] = {
            "name":           name,
            "brand":          row.get("brand", name),
            "address":        row.get("address", ""),
            "postcode":       "",
            "lat":            lat_f,
            "lng":            lng_f,
            "distance":       haversine(CENTRE_LAT, CENTRE_LNG, lat_f, lng_f) if lat_f and lng_f else 0,
            "is_supermarket": False,
            "is_motorway":    False,
            "unleaded":       unleaded,
            "diesel":         diesel,
            "updated":        parse_sheets_date(row.get("date", "")),
            "cached":         True
        }
        extra_count += 1

    log(f"Sheets fallback: {fallback_count} gaps filled, {extra_count} stations added")

    # ── National averages ─────────────────────────────────────────────────────
    log("Calculating national averages...")
    all_unleaded, all_diesel = [], []
    for p in all_prices:
        for fp in p.get("fuel_prices", []):
            fuel_type = fp.get("fuel_type", "").upper()
            price     = fp.get("price")
            if not valid_price(price):
                continue
            if "E10" in fuel_type:
                all_unleaded.append(float(price))
            elif "B7" in fuel_type or "DIESEL" in fuel_type:
                all_diesel.append(float(price))

    national_avg = {
        "unleaded": round(sum(all_unleaded) / len(all_unleaded), 1) if all_unleaded else None,
        "diesel":   round(sum(all_diesel)   / len(all_diesel),   1) if all_diesel   else None
    }

    # Fallback: if mandatory API returned no prices, derive average from local station data
    if national_avg["unleaded"] is None:
        local_ul = [s["unleaded"] for s in local_stations.values()
                    if s.get("unleaded") and s["unleaded"] >= PRICE_FLOOR]
        national_avg["unleaded"] = round(sum(local_ul) / len(local_ul), 1) if local_ul else None
        if national_avg["unleaded"]:
            log(f"National avg fallback (local data): unleaded={national_avg['unleaded']}p")

    if national_avg["diesel"] is None:
        local_di = [s["diesel"] for s in local_stations.values()
                    if s.get("diesel") and s["diesel"] >= PRICE_FLOOR]
        national_avg["diesel"] = round(sum(local_di) / len(local_di), 1) if local_di else None
        if national_avg["diesel"]:
            log(f"National avg fallback (local data): diesel={national_avg['diesel']}p")

    log(f"National averages: unleaded={national_avg['unleaded']}p, diesel={national_avg['diesel']}p")

    # ── Build output ──────────────────────────────────────────────────────────
    log("Processing and filtering...")
    stations_list = list(local_stations.values())
    for s in stations_list:
        s.pop("node_id", None)

    output = {
        "nationalAvg":  national_avg,
        "lastUpdated":  datetime.now(timezone.utc).isoformat(),
        "stationCount": len(stations_list),
        "stations":     stations_list
    }

    ul_prices = [s["unleaded"] for s in stations_list if s["unleaded"]]
    di_prices = [s["diesel"]   for s in stations_list if s["diesel"]]
    if ul_prices:
        log(f"Unleaded: {min(ul_prices)}p - {max(ul_prices)}p")
    if di_prices:
        log(f"Diesel: {min(di_prices)}p - {max(di_prices)}p")

    cached = sum(1 for s in stations_list if s.get("cached"))
    live   = len(stations_list) - cached
    log(f"Stations: {len(stations_list)} total ({live} live, {cached} cached)")

    # Safety check — don't overwrite good data with sparse results
    MIN_STATIONS = 50
    if len(stations_list) < MIN_STATIONS:
        log(f"ABORT: Only {len(stations_list)} stations — below minimum of {MIN_STATIONS}. Existing data preserved.")
        exit(1)

    with open(OUTPUT_FILE, "w") as f:
        json.dump(output, f, indent=2)
    log(f"Saved to {OUTPUT_FILE}")

    # ── Git commit and push ───────────────────────────────────────────────────
    git_push()


if __name__ == "__main__":
    main()
