import requests
import json
import os
import csv
import io
from datetime import datetime, timezone

# ── Credentials ───────────────────────────────────────────────────────────────
CLIENT_ID     = "OXaCtJ25MBEQs0OHobvSf8l3A5ztgsM2"
CLIENT_SECRET = "XMYqgyjvqSjy4MS5BDS6zrKty8nluY29JEOLaXRyXBRHMz6tWmyWTD8Nl7qIeRAE"

BASE_URL      = "https://www.fuel-finder.service.gov.uk"
TOKEN_URL     = f"{BASE_URL}/api/v1/oauth/generate_access_token"
PRICES_URL    = f"{BASE_URL}/api/v1/pfs/fuel-prices"
INFO_URL      = f"{BASE_URL}/api/v1/pfs"

# ── Google Sheets fallback ────────────────────────────────────────────────────
SHEET_ID      = "1HE-K4RVMbwWOuF6hy-CJg1G5kFWtChpK4w1WKnWqjTQ"
SHEET_GID     = "1435371472"
SHEET_CSV_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={SHEET_GID}"

# ── Output ────────────────────────────────────────────────────────────────────
OUTPUT_FILE   = os.path.expanduser("~/stations.json")

# ── Geographic filter ─────────────────────────────────────────────────────────
LAT_MIN, LAT_MAX = 53.05, 53.40
LNG_MIN, LNG_MAX = -3.35, -2.80

# ── Price floor ───────────────────────────────────────────────────────────────
PRICE_FLOOR = 115.0


def log(msg):
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {msg}")


def get_token():
    log("Authenticating...")
    r = requests.post(TOKEN_URL, json={
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET
    })
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
    while True:
        params = {"batch-number": batch}
        if extra_params:
            params.update(extra_params)
        r = requests.get(url, headers=headers, params=params)
        if r.status_code in (400, 403, 404):
            break
        r.raise_for_status()
        data = r.json()
        if not data:
            break
        all_records.extend(data)
        log(f"  Batch {batch}: {len(data)} items (total: {len(all_records)})")
        if len(data) < 500:
            break
        batch += 1
    log(f"Total records fetched: {len(all_records)}")
    return all_records


def in_area(lat, lng):
    try:
        return LAT_MIN <= float(lat) <= LAT_MAX and LNG_MIN <= float(lng) <= LNG_MAX
    except (TypeError, ValueError):
        return False


def valid_price(p):
    try:
        return float(p) >= PRICE_FLOOR
    except (TypeError, ValueError):
        return False


def load_sheets_fallback():
    """Read most recent price per station from Google Sheets."""
    log("Loading Google Sheets fallback data...")
    try:
        r = requests.get(SHEET_CSV_URL)
        r.raise_for_status()
        reader = csv.DictReader(io.StringIO(r.text))
        stations = {}
        for row in reader:
            name = row.get("station_name", "").strip()
            if not name:
                continue
            date_str = row.get("date", "")
            # Keep the most recent row per station
            if name not in stations or date_str > stations[name]["date"]:
                stations[name] = row
        log(f"Sheets fallback: {len(stations)} stations loaded")
        return stations
    except Exception as e:
        log(f"Warning: Could not load Sheets fallback — {e}")
        return {}


def main():
    log("=" * 50)
    log("Deeside Fuel Prices — API Update")
    log("=" * 50)

    # Step 1 — OAuth token
    token = get_token()

    # Step 2 — Load Sheets fallback
    sheets_data = load_sheets_fallback()

    # Step 3 — Fetch all station info from new API
    log("Fetching station info...")
    all_info = fetch_all_batches(INFO_URL, token)

    # Step 4 — Filter to local area
    local_stations = {}
    for s in all_info:
        loc = s.get("location", {})
        lat = loc.get("latitude")
        lng = loc.get("longitude")
        if not in_area(lat, lng):
            continue
        local_stations[s["node_id"]] = {
            "node_id":  s["node_id"],
            "name":     s.get("trading_name", ""),
            "brand":    s.get("brand_name", s.get("trading_name", "")),
            "address":  loc.get("address", ""),
            "postcode": loc.get("postcode", ""),
            "lat":      float(lat),
            "lng":      float(lng),
            "unleaded": None,
            "diesel":   None,
            "updated":  None,
            "cached":   False
        }

    log(f"Found {len(local_stations)} stations in area from new API")

    # Step 5 — Fetch prices from new API
    log("Fetching fuel prices...")
    all_prices = fetch_all_batches(PRICES_URL, token)

    # Step 6 — Merge prices into local stations
    for p in all_prices:
        node_id = p.get("node_id")
        if node_id not in local_stations:
            continue
        for fp in p.get("fuel_prices", []):
            fuel_type = fp.get("fuel_type", "").upper()
            price     = fp.get("price")
            updated   = fp.get("effective_from") or fp.get("last_updated")
            if not valid_price(price):
                continue
            if fuel_type == "E10":
                local_stations[node_id]["unleaded"] = float(price)
            elif fuel_type in ("B7", "DIESEL"):
                local_stations[node_id]["diesel"] = float(price)
            if updated:
                local_stations[node_id]["updated"] = updated

    # Step 7 — Fill gaps with Sheets fallback for existing local stations
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
            station["updated"] = row.get("date", "")
            fallback_count += 1
            log(f"  Sheets fallback used for: {name}")

    # Step 8 — Add Sheets-only stations not found in new API at all
    api_names = {s["name"] for s in local_stations.values()}
    extra_count = 0
    for name, row in sheets_data.items():
        if name in api_names:
            continue
        unleaded = float(row["unleaded"]) if valid_price(row.get("unleaded")) else None
        diesel   = float(row["diesel"])   if valid_price(row.get("diesel"))   else None
        if not unleaded and not diesel:
            continue
        # Try to get coords from sheet if present
        try:
            lat = float(row.get("lat", 0) or 0)
            lng = float(row.get("lng", 0) or 0)
        except ValueError:
            lat, lng = 0.0, 0.0
        local_stations["sheets_" + name] = {
            "name":     name,
            "brand":    row.get("brand", name),
            "address":  row.get("address", ""),
            "postcode": "",
            "lat":      lat,
            "lng":      lng,
            "unleaded": unleaded,
            "diesel":   diesel,
            "updated":  row.get("date", ""),
            "cached":   True
        }
        extra_count += 1

    log(f"Fallback: {fallback_count} gaps filled, {extra_count} Sheets-only stations added")

    # Step 9 — National averages from new API data
    log("Processing and filtering...")
    all_unleaded, all_diesel = [], []
    for p in all_prices:
        for fp in p.get("fuel_prices", []):
            fuel_type = fp.get("fuel_type", "").upper()
            price     = fp.get("price")
            if not valid_price(price):
                continue
            if fuel_type == "E10":
                all_unleaded.append(float(price))
            elif fuel_type in ("B7", "DIESEL"):
                all_diesel.append(float(price))

    national_avg = {
        "unleaded": round(sum(all_unleaded) / len(all_unleaded), 1) if all_unleaded else None,
        "diesel":   round(sum(all_diesel)   / len(all_diesel),   1) if all_diesel   else None
    }

    # Step 10 — Build output
    stations_list = list(local_stations.values())
    for s in stations_list:
        s.pop("node_id", None)  # Remove internal field

    output = {
        "nationalAvg":  national_avg,
        "lastUpdated":  datetime.now(timezone.utc).isoformat(),
        "stationCount": len(stations_list),
        "stations":     stations_list
    }

    # Summary
    ul_prices = [s["unleaded"] for s in stations_list if s["unleaded"]]
    di_prices = [s["diesel"]   for s in stations_list if s["diesel"]]
    if ul_prices:
        log(f"Unleaded: {min(ul_prices)}p - {max(ul_prices)}p")
    if di_prices:
        log(f"Diesel: {min(di_prices)}p - {max(di_prices)}p")

    cached = sum(1 for s in stations_list if s.get("cached"))
    live   = len(stations_list) - cached
    log(f"Stations: {len(stations_list)} total ({live} live from new API, {cached} from Sheets fallback)")

    with open(OUTPUT_FILE, "w") as f:
        json.dump(output, f, indent=2)
    log(f"Saved to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
