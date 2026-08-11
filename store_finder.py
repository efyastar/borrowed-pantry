"""Find real grocery stores near a location via OpenStreetMap, persist them to CockroachDB."""
import json
import urllib.request
import urllib.parse
from db import get_connection

OVERPASS_URL = "https://overpass-api.de/api/interpreter"

SPECIALTY_HINTS = [
    "african", "afro", "nigerian", "ghana", "ghanaian", "caribbean",
    "halal", "international", "world market", "ethnic", "tropical",
    "asian", "oriental", "indian", "bazar", "bazaar", "mercado",
    "carniceria", "supermercado", "latino", "hispanic", "mediterranean",
    "middle east", "persian", "pars", "global", "spice",
]

EXCLUDE_HINTS = [
    "chevron", "shell", "exxon", "mobil", "76", "bp", "arco", "texaco",
    "circle k", "7-eleven", "speedway", "wawa", "sheetz", "gas",
]


def _build_query(lat: float, lng: float, radius_m: int) -> str:
    return f"""
    [out:json][timeout:25];
    (
      node["shop"~"supermarket|greengrocer"](around:{radius_m},{lat},{lng});
      way["shop"~"supermarket|greengrocer"](around:{radius_m},{lat},{lng});
    );
    out center tags 40;
    """


def fetch_nearby_stores(lat: float, lng: float, radius_m: int = 15000) -> list[dict]:
    """Query Overpass for grocery stores near a point. Returns [] on any failure."""
    query = _build_query(lat, lng, radius_m)
    data = urllib.parse.urlencode({"data": query}).encode()
    req = urllib.request.Request(
        OVERPASS_URL, data=data,
        headers={"User-Agent": "BorrowedPantry/1.0 (hackathon project)"},
    )
    try:
        with urllib.request.urlopen(req, timeout=25) as resp:
            payload = json.loads(resp.read())
    except Exception as e:
        print(f"Overpass lookup failed: {e}")
        return []

    stores = []
    for element in payload.get("elements", []):
        tags = element.get("tags", {})
        name = tags.get("name")
        if not name:
            continue

        if element["type"] == "node":
            s_lat, s_lng = element.get("lat"), element.get("lon")
        else:
            center = element.get("center", {})
            s_lat, s_lng = center.get("lat"), center.get("lon")
        if s_lat is None or s_lng is None:
            continue

        parts = [
            tags.get("addr:housenumber", ""),
            tags.get("addr:street", ""),
            tags.get("addr:city", ""),
        ]
        address = " ".join(p for p in parts if p).strip() or "Address not listed"

        haystack = f"{name} {tags.get('cuisine','')} {tags.get('origin','')}".lower()
        if any(x in haystack for x in EXCLUDE_HINTS):
            continue
        store_type = "african" if any(h in haystack for h in SPECIALTY_HINTS) else "general"

        stores.append({
            "name": name.strip(),
            "chain": tags.get("brand") or tags.get("operator"),
            "address": address,
            "lat": s_lat,
            "lng": s_lng,
            "store_type": store_type,
        })
    return stores


def save_stores(stores: list[dict]) -> int:
    """Insert any stores we do not already have. Returns count of new rows."""
    added = 0
    with get_connection() as conn:
        with conn.cursor() as cur:
            for s in stores:
                cur.execute("SELECT 1 FROM stores WHERE name = %s;", (s["name"],))
                if cur.fetchone():
                    continue
                cur.execute(
                    """INSERT INTO stores (name, chain, address, lat, lng, store_type)
                       VALUES (%s, %s, %s, %s, %s, %s) ON CONFLICT DO NOTHING;""",
                    (s["name"], s["chain"], s["address"], s["lat"], s["lng"], s["store_type"]),
                )
                conn.commit()
                added += 1
    return added


def ensure_stores_near(lat: float, lng: float) -> int:
    """Look up and persist real stores near a location. Safe to call repeatedly."""
    found = fetch_nearby_stores(lat, lng)
    if not found:
        return 0
    return save_stores(found)


if __name__ == "__main__":
    import sys
    lat = float(sys.argv[1]) if len(sys.argv) > 2 else 30.3322
    lng = float(sys.argv[2]) if len(sys.argv) > 2 else -81.6557
    print(f"Looking up stores near {lat}, {lng}...")
    results = fetch_nearby_stores(lat, lng)
    print(f"Found {len(results)} stores:")
    for r in results[:15]:
        mark = " [african/intl]" if r["store_type"] == "african" else ""
        print(f"  {r['name']} - {r['address']}{mark}")
    added = save_stores(results)
    print(f"Saved {added} new stores.")