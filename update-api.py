#!/usr/bin/env python3
"""
Deeside Fuel Prices — API Auto-Updater
========================================
Fetches live fuel prices from the GOV.UK Fuel Finder API,
filters to the Deeside/Flintshire/Chester area, and commits
stations.json to GitHub.

Run every 30 minutes via crontab:
  crontab -e
  */30 * * * * /usr/bin/python3 /Users/jonsheppard/deeside-fuel-prices/update-api.py >> /Users/jonsheppard/deeside-fuel-prices/update.log 2>&1

Requires: GITHUB_TOKEN environment variable (or hardcode below)
"""

import json, math, urllib.request, urllib.error, base64, os, sys
from datetime import datetime, timezone

# ── CONFIG ──
API_BASE = "https://www.fuel-finder.service.gov.uk/api/v1"
CLIENT_ID = "OXaCtJ25MBEQs0OHobvSf8l3A5ztgsM2"
CLIENT_SECRET = "XMYqgyjvqSjy4MS5BDS6zrKty8nluY29JEOLaXRyXBRHMz6tWmyWTD8Nl7qIeRAE"

GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "YOUR_TOKEN_HERE")  # Set via: export GITHUB_TOKEN=ghp_xxx
GITHUB_REPO = "jonathansheppard/deeside-fuel-prices"
GITHUB_FILE = "stations.json"

DEESIDE_LAT = 53.2089
DEESIDE_LNG = -3.0330
MAX_DISTANCE = 25  # miles

NATIONAL_AVG_UNLEADED = 131.7
NATIONAL_AVG_DIESEL = 141.5

TARGET_POSTCODES = [
    'CH1','CH2','CH3','CH4','CH5','CH6','CH7','CH8',
    'CH41','CH42','CH43','CH44','CH45','CH46','CH47','CH48','CH49',
    'CH60','CH61','CH62','CH63','CH64','CH65','CH66',
    'LL11','LL12','LL13','LL14','LL15','LL16','LL17','LL18','LL19','LL20'
]


def log(msg):
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {msg}")


def haversine(lat1, lon1, lat2, lon2):
    R = 3959
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon/2)**2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))


def api_request(url, method="GET", data=None, headers=None):
    if headers is None:
        headers = {}
    headers["Content-Type"] = "application/json"
    
    body = json.dumps(data).encode() if data else None
    req = urllib.request.Request(url, data=body, method=method, headers=headers)
    
    try:
        resp = urllib.request.urlopen(req)
        return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        error_body = e.read().decode() if e.fp else ""
        log(f"HTTP {e.code}: {error_body[:500]}")
        raise


def get_token():
    log("Authenticating...")
    result = api_request(
        f"{API_BASE}/oauth/generate_access_token",
        method="POST",
        data={"client_id": CLIENT_ID, "client_secret": CLIENT_SECRET}
    )
    if result.get("success"):
        token = result["data"]["access_token"]
        log("Token obtained successfully")
        return token
    else:
        raise Exception(f"Auth failed: {result.get('message')}")


def fetch_all_batches(endpoint, token):
    """Fetch all batches from a paginated API endpoint."""
    all_items = []
    batch = 1
    headers = {"Authorization": f"Bearer {token}"}
    
    while True:
        url = f"{API_BASE}/{endpoint}?batch-number={batch}"
        try:
            items = api_request(url, headers=headers)
            if not isinstance(items, list) or len(items) == 0:
                break
            all_items.extend(items)
            log(f"  Batch {batch}: {len(items)} items (total: {len(all_items)})")
            if len(items) < 500:
                break
            batch += 1
        except Exception as e:
            log(f"  Batch {batch} failed: {e}")
            break
    
    return all_items


def matches_postcode(postcode):
    pc = postcode.upper().strip()
    return any(pc.startswith(p) for p in TARGET_POSTCODES)


def process_data(stations_raw, prices_raw):
    """Merge station info with prices, filter to local area."""
    
    # Build station lookup
    station_map = {}
    for s in stations_raw:
        loc = s.get("location", {})
        pc = loc.get("postcode", "")
        if not matches_postcode(pc):
            continue
        if s.get("permanent_closure") or s.get("temporary_closure"):
            continue
        
        lat = loc.get("latitude")
        lng = loc.get("longitude")
        if not lat or not lng:
            continue
        station_map[nid]["diesel"] = diesel
        station_map[nid]["updated"] = latest_update or ""
    
    # Build final list
    stations = []
    sid = 1
    for nid, s in station_map.items():
        if s.get("unleaded") is None and s.get("diesel") is None:
            continue
        s["id"] = sid
        stations.append(s)
        sid += 1
    
    stations.sort(key=lambda x: x.get("unleaded") or 999)

    # Manual additions — local stations not reporting prices to the scheme
    manual_stations = [
        {
            "name": "Asda Quay Express (Esso)",
            "brand": "ESSO",
            "address": "Church Street, Connah's Quay, CH5 4AS",
            "lat": 53.22449,
            "lng": -3.071442,
            "unleaded": None,
            "diesel": None,
            "updated": "",
            "distance": 1.2,
            "is_supermarket": False,
            "is_motorway": False,
            "note": "Not reporting prices"
        },
        {
            "name": "Asda Deeside Express Petrol",
            "brand": "ASDA",
            "address": "Parkway, Deeside, CH5 2NS",
            "lat": 53.2280,
            "lng": -3.0120,
            "unleaded": None,
            "diesel": None,
            "updated": "",
            "distance": 1.8,
            "is_supermarket": True,
            "is_motorway": False,
            "note": "Not reporting prices"
        },
        {
            "name": "Asda Queensferry Petrol",
            "brand": "ASDA",
            "address": "Aston Road, Queensferry, CH5 1TQ",
            "lat": 53.2050,
            "lng": -3.0265,
            "unleaded": None,
            "diesel": None,
            "updated": "",
            "distance": 0.8,
            "is_supermarket": True,
            "is_motorway": False,
            "note": "Not reporting prices"
        }
    ]
    for ms in manual_stations:
        ms["id"] = sid
        stations.append(ms)
        sid += 1

    return stations


def commit_to_github(json_content):
    """Commit stations.json to GitHub."""
    if GITHUB_TOKEN == "YOUR_TOKEN_HERE":
        log("No GITHUB_TOKEN set. Saving locally only.")
        return False
    
    api_url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{GITHUB_FILE}"
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Content-Type": "application/json",
        "User-Agent": "Deeside-Fuel-Updater"
    }
    
    # Get current SHA
    try:
        req = urllib.request.Request(api_url, headers=headers)
        resp = urllib.request.urlopen(req)
        current = json.loads(resp.read().decode())
        sha = current["sha"]
        
        # Check if content changed
        existing = base64.b64decode(current["content"]).decode()
        if existing.strip() == json_content.strip():
            log("No price changes detected. Skipping commit.")
            return True
    except urllib.error.HTTPError:
        sha = None  # File doesn't exist yet
    
    # Commit
    encoded = base64.b64encode(json_content.encode()).decode()
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    body = {"message": f"Update fuel prices {timestamp}", "content": encoded}
    if sha:
        body["sha"] = sha
    
    req = urllib.request.Request(
        api_url,
        data=json.dumps(body).encode(),
        method="PUT",
        headers=headers
    )
    resp = urllib.request.urlopen(req)
    result = json.loads(resp.read().decode())
    log(f"Committed to GitHub: {result['commit']['sha'][:8]}")
    return True


def main():
    log("=" * 50)
    log("Deeside Fuel Prices — API Update")
    log("=" * 50)
    
    try:
        # 1. Authenticate
        token = get_token()
        
        # 2. Fetch stations
        log("Fetching station info...")
        stations_raw = fetch_all_batches("pfs", token)
        log(f"Total stations fetched: {len(stations_raw)}")
        
        # 3. Fetch prices
        log("Fetching fuel prices...")
        prices_raw = fetch_all_batches("pfs/fuel-prices", token)
        log(f"Total price records fetched: {len(prices_raw)}")
        
        # 4. Process
        log("Processing and filtering...")
        stations = process_data(stations_raw, prices_raw)
        
        if not stations:
            log("ERROR: No stations found after filtering!")
            sys.exit(1)
        
        # 4b. Calculate national averages from ALL UK stations
        all_unleaded = []
        all_diesel = []
        for p in prices_raw:
            for fp in p.get("fuel_prices", []):
                price = fp.get("price")
                if not price or price <= 0:
                    continue
                if fp.get("fuel_type") == "E10":
                    all_unleaded.append(float(price))
                elif fp.get("fuel_type") == "B7_STANDARD":
                    all_diesel.append(float(price))
        
        natl_unleaded = round(sum(all_unleaded) / len(all_unleaded), 1) if all_unleaded else 131.7
        natl_diesel = round(sum(all_diesel) / len(all_diesel), 1) if all_diesel else 141.5
        log(f"National avg: {natl_unleaded}p unleaded ({len(all_unleaded)} stations), {natl_diesel}p diesel ({len(all_diesel)} stations)")
        
        unleaded = [s["unleaded"] for s in stations if s.get("unleaded")]
        diesel = [s["diesel"] for s in stations if s.get("diesel")]
        within_10 = len([s for s in stations if s["distance"] <= 10])
        
        log(f"Stations: {len(stations)} ({within_10} core / {len(stations) - within_10} wider)")
        if unleaded:
            log(f"Unleaded: {min(unleaded):.1f}p - {max(unleaded):.1f}p")
        if diesel:
            log(f"Diesel: {min(diesel):.1f}p - {max(diesel):.1f}p")
        
        # 5. Build output
        output = {
            "nationalAvg": {
                "unleaded": natl_unleaded,
                "diesel": natl_diesel
            },
            "lastUpdated": datetime.now(timezone.utc).isoformat(),
            "stationCount": len(stations),
            "stations": stations
        }
        
        json_content = json.dumps(output, indent=2)
        
        # 6. Save locally
        script_dir = os.path.dirname(os.path.abspath(__file__))
        local_path = os.path.join(script_dir, "stations.json")
        with open(local_path, "w") as f:
            f.write(json_content)
        log(f"Saved to {local_path}")
        
        # 7. Commit to GitHub
        commit_to_github(json_content)
        
        log("Update complete!")
        
    except Exception as e:
        log(f"ERROR: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
