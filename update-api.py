import requests
import json
import os
from datetime import datetime, timezone

# ── Credentials ───────────────────────────────────────────────────────────────
CLIENT_ID     = "OXaCtJ25MBEQs0OHobvSf8l3A5ztgsM2"
CLIENT_SECRET = "XMYqgyjvqSjy4MS5BDS6zrKty8nluY29JEOLaXRyXBRHMz6tWmyWTD8Nl7qIeRAE"

BASE_URL      = "https://api.fuelfinder.service.gov.uk"
TOKEN_URL     = f"{BASE_URL}/api/v1/oauth/generate_access_token"
PRICES_URL    = f"{BASE_URL}/api/v1/pfs/fuel-prices"
INFO_URL      = f"{BASE_URL}/api/v1/pfs"

# Output file — same location your map already reads from
OUTPUT_FILE   = os.path.expanduser("~/fuel_prices.json")

# ── Geographic filter — bounding box covering Deeside / Flintshire / Chester ──
LAT_MIN, LAT_MAX = 53.05, 53.40
LNG_MIN, LNG_MAX = -3.35, -2.80


def get_token():
    """Step 1: Exchange credentials for an access token."""
    print("Getting access token...")
    r = requests.post(TOKEN_URL, json={
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET
    })
    r.raise_for_status()
    data = r.json()
    token = data.get("data", {}).get("access_token") or data.get("access_token")
    if not token:
        raise ValueError(f"No token in response: {data}")
    print("Token obtained.")
    return token


def fetch_all_batches(url, token, params=None):
    """Fetch all paginated batches from an endpoint (500 records per batch)."""
    headers = {"Authorization": f"Bearer {token}"}
    all_records = []
    batch = 1
    while True:
        p = {"batch-number": batch}
        if params:
            p.update(params)
        print(f"  Fetching batch {batch} from {url.split('/')[-1]}...")
        r = requests.get(url, headers=headers, params=p)
        if r.status_code in (400, 403, 404):
            break
        r.raise_for_status()
        data = r.json()
        if not data:
            break
        all_records.extend(data)
        if len(data) < 500:
            break  # Last batch
        batch += 1
    print(f"  Total records: {len(all_records)}")
    return all_records


def in_area(lat, lng):
    """Return True if coordinates fall within our target area."""
    try:
        return LAT_MIN <= float(lat) <= LAT_MAX and LNG_MIN <= float(lng) <= LNG_MAX
    except (TypeError, ValueError):
        return False


def main():
    # Step 1 — get token
    token = get_token()

    # Step 2 — fetch all station info (name, brand, location)
    print("Fetching station info...")
    all_info = fetch_all_batches(INFO_URL, token)

    # Build a lookup dict keyed by node_id, filtering to our area
    print("Filtering to Deeside/Flintshire area...")
    local_stations = {}
    for s in all_info:
        loc = s.get("location", {})
        lat = loc.get("latitude")
        lng = loc.get("longitude")
        if in_area(lat, lng):
            local_stations[s["node_id"]] = {
                "site_id":   s["node_id"],
                "name":      s.get("trading_name", ""),
                "brand":     s.get("brand_name", s.get("trading_name", "")),
                "address":   loc.get("address", ""),
                "postcode":  loc.get("postcode", ""),
                "lat":       float(lat),
                "lng":       float(lng),
                "E10":       None,
                "B7":        None,
                "E5":        None,
                "SDV":       None,
                "last_updated": None
            }

    print(f"Found {len(local_stations)} stations in area.")

    # Step 3 — fetch all prices
    print("Fetching fuel prices...")
    all_prices = fetch_all_batches(PRICES_URL, token)

    # Step 4 — merge prices into local stations
    matched = 0
    for p in all_prices:
        node_id = p.get("node_id")
        if node_id not in local_stations:
            continue
        for fp in p.get("fuel_prices", []):
            fuel_type = fp.get("fuel_type", "").upper()
            price     = fp.get("price")
            updated   = fp.get("effective_from") or fp.get("last_updated")
            if fuel_type == "E10":
                local_stations[node_id]["E10"] = price
            elif fuel_type in ("B7", "DIESEL"):
                local_stations[node_id]["B7"] = price
            elif fuel_type == "E5":
                local_stations[node_id]["E5"] = price
            elif fuel_type in ("SDV", "SUPER DIESEL"):
                local_stations[node_id]["SDV"] = price
            if updated and not local_stations[node_id]["last_updated"]:
                local_stations[node_id]["last_updated"] = updated
        matched += 1

    print(f"Prices matched for {matched} local stations.")

    # Step 5 — write output
    output = {
        "last_updated": datetime.now(timezone.utc).isoformat(),
        "stations": list(local_stations.values())
    }

    with open(OUTPUT_FILE, "w") as f:
        json.dump(output, f, indent=2)

    print(f"Done. Saved {len(local_stations)} stations to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
