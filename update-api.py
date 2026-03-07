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

import json, math, urllib.request, urllib.error, base64, os, sys, re
from datetime import datetime, timezone
from html.parser import HTMLParser

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

# Fallback national averages — updated if live fetch succeeds
NATIONAL_AVG_UNLEADED_FALLBACK = 136.5
NATIONAL_AVG_DIESEL_FALLBACK = 149.5

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


# ── NATIONAL AVERAGE FETCHER ──────────────────────────────────────────────────

class RACTableParser(HTMLParser):
    """Minimal HTML parser to extract fuel price table data from RAC Fuel Watch."""
    def __init__(self):
        super().__init__()
        self.in_table = False
        self.in_cell = False
        self.current_row = []
        self.all_rows = []
        self.depth = 0

    def handle_starttag(self, tag, attrs):
        if tag == 'table':
            self.in_table = True
            self.depth += 1
        if self.in_table and tag in ('td', 'th'):
            self.in_cell = True
            self.current_cell = ''

    def handle_endtag(self, tag):
        if tag == 'table':
            self.depth -= 1
            if self.depth == 0:
                self.in_table = False
        if self.in_table and tag in ('td', 'th'):
            self.in_cell = False
            self.current_row.append(self.current_cell.strip())
        if self.in_table and tag == 'tr':
            if self.current_row:
                self.all_rows.append(self.current_row)
            self.current_row = []

    def handle_data(self, data):
        if self.in_cell:
            self.current_cell += data


def get_national_averages():
    """
    Fetch current UK average fuel prices from RAC Fuel Watch.
    Falls back to hardcoded values if fetch fails.
    """
    try:
        log("Fetching national average prices from RAC Fuel Watch...")
        req = urllib.request.Request(
            'https://www.rac.co.uk/drive/advice/fuel-watch/',
            headers={'User-Agent': 'Mozilla/5.0 (compatible; DeesideFuelBot/1.0)'}
        )
        resp = urllib.request.urlopen(req, timeout=15)
        html = resp.read().decode('utf-8', errors='replace')

        parser = RACTableParser()
        parser.feed(html)

        unleaded = None
        diesel = None

        for row in parser.all_rows:
            if len(row) < 2:
                continue
            label = row[0].lower().strip()
            # Extract numeric value — strip 'p', commas, spaces
            raw = re.sub(r'[^\d.]', '', row[1])
            if not raw:
                continue
            try:
                val = float(raw)
            except ValueError:
                continue

            # Only accept plausible pence-per-litre values
            if not (100 < val < 250):
                continue

            if label == 'unleaded' and unleaded is None:
                unleaded = val
            elif label == 'diesel' and diesel is None:
                diesel = val

        if unleaded and diesel:
            log(f"National averages: unleaded {unleaded}p, diesel {diesel}p")
            return {'unleaded': unleaded, 'diesel': diesel}
        else:
            log("Could not parse RAC table — using fallback averages")
            return {'unleaded': NATIONAL_AVG_UNLEADED_FALLBACK, 'diesel': NATIONAL_AVG_DIESEL_FALLBACK}

    except Exception as e:
        log(f"National average fetch failed ({e}) — using fallback averages")
        return {'unleaded': NATIONAL_AVG_UNLEADED_FALLBACK, 'diesel': NATIONAL_AVG_DIESEL_FALLBACK}


# ── MAIN PIPELINE ─────────────────────────────────────────────────────────────

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
        
        dist = round(haversine(DEESIDE_LAT, DEESIDE_LNG, float(lat), float(lng)), 1)
        if dist > MAX_DISTANCE:
            continue
        
        addr_parts = [loc.get("address_line_1", ""), loc.get("city", ""), pc]
        address = ", ".join([p for p in addr_parts if p and p.strip()])
        
        station_map[s["node_id"]] = {
            "name": s.get("trading_name", "Unknown"),
            "brand": (s.get("brand_name") or s.get("trading_name") or "INDEPENDENT").upper(),
            "address": address,
            "lat": float(lat),
            "lng": float(lng),
            "distance": dist,
            "is_supermarket": s.get("is_supermarket_service_station", False),
            "is_motorway": s.get("is_motorway_service_station", False),
        }
    
    # Merge prices
    for p in prices_raw:
        nid = p.get("node_id")
        if nid not in station_map:
            continue
        
        unleaded = None
        diesel = None
        latest_update = None
        
        for fp in p.get("fuel_prices", []):
            ft = fp.get("fuel_type")
            price = fp.get("price")
            updated = fp.get("price_last_updated")
            
            if ft == "E10":
                unleaded = float(price) if price else None
            elif ft == "E5" and unleaded is None:
                unleaded = float(price) if price else None
            
            if ft == "B7_STANDARD":
                diesel = float(price) if price else None
            elif ft == "B7_PREMIUM" and diesel is None:
                diesel = float(price) if price else None
            
            if updated:
                latest_update = updated
        
        station_map[nid]["unleaded"] = unleaded
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
        # 1. Fetch national averages from RAC Fuel Watch
        national_avg = get_national_averages()

        # 2. Authenticate
        token = get_token()
        
        # 3. Fetch stations
        log("Fetching station info...")
        stations_raw = fetch_all_batches("pfs", token)
        log(f"Total stations fetched: {len(stations_raw)}")
        
        # 4. Fetch prices
        log("Fetching fuel prices...")
        prices_raw = fetch_all_batches("pfs/fuel-prices", token)
        log(f"Total price records fetched: {len(prices_raw)}")
        
        # 5. Process
        log("Processing and filtering...")
        stations = process_data(stations_raw, prices_raw)
        
        if not stations:
            log("ERROR: No stations found after filtering!")
            sys.exit(1)
        
        unleaded = [s["unleaded"] for s in stations if s.get("unleaded")]
        diesel = [s["diesel"] for s in stations if s.get("diesel")]
        within_10 = len([s for s in stations if s["distance"] <= 10])
        
        log(f"Stations: {len(stations)} ({within_10} core / {len(stations) - within_10} wider)")
        if unleaded:
            log(f"Unleaded: {min(unleaded):.1f}p - {max(unleaded):.1f}p")
        if diesel:
            log(f"Diesel: {min(diesel):.1f}p - {max(diesel):.1f}p")
        
        # 6. Build output
        output = {
            "nationalAvg": national_avg,
            "lastUpdated": datetime.now(timezone.utc).isoformat(),
            "stationCount": len(stations),
            "stations": stations
        }
        
        json_content = json.dumps(output, indent=2)
        
        # 7. Save locally
        script_dir = os.path.dirname(os.path.abspath(__file__))
        local_path = os.path.join(script_dir, "stations.json")
        with open(local_path, "w") as f:
            f.write(json_content)
        log(f"Saved to {local_path}")
        
        # 8. Commit to GitHub
        commit_to_github(json_content)
        
        log("Update complete!")
        
    except Exception as e:
        log(f"ERROR: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
