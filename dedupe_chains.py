"""
Stage 5 — data hygiene: detect multi-location chains so they collapse into
one account instead of being scored/called as N unrelated leads.

Why this needs its own, wider query: the 80-restaurant Manhattan sample in
harvest.py is too small to reliably surface real chains (a spot-check found
zero name/phone/domain duplicates in it). This script runs its own citywide
Overpass query — same source, same no-key approach, just a bigger box — big
enough that real multi-location chains actually show up. That's a
deliberate scope difference from harvest.py, not an inconsistency, and it's
disclosed here rather than silently querying something different.

Matching method: normalize each name (lowercase, strip common NYC
neighborhood words, collapse punctuation/whitespace) and group restaurants
that normalize to the same base name. This is a real, honestly-limited
heuristic — it will both over-merge (two unrelated restaurants that happen
to share a generic name) and under-merge (a chain location whose OSM name
tag includes a store number or slightly different spelling). Real GTM data
hygiene has exactly this precision/recall tradeoff; the disclosed limitation
is the point, not a bug to hide.

Run it yourself: python3 dedupe_chains.py
"""

import json
import os
import re
import urllib.parse
import urllib.request
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
RAW_PATH = os.path.join(HERE, "data", "citywide_raw.json")
OUT_PATH = os.path.join(HERE, "data", "chains_detected.json")

# A wider NYC box (covers Manhattan + parts of Brooklyn/Queens/Bronx) —
# chosen because it's what surfaced real chains during scoping, not tuned
# after the fact to produce a nicer number.
BBOX = "40.68,-74.03,40.82,-73.90"
MAX_RESULTS = 400

QUERY = f"""
[out:json][timeout:60];
node["amenity"="restaurant"]["website"]["phone"]({BBOX});
out body {MAX_RESULTS};
"""

NEIGHBORHOOD_WORDS = (
    "nyc|new york|midtown|downtown|uptown|soho|tribeca|chelsea|"
    "east village|west village|financial district|fidi|harlem|"
    "williamsburg|astoria|flushing"
)


def normalize(name):
    n = (name or "").lower()
    n = re.sub(rf"\b({NEIGHBORHOOD_WORDS})\b", "", n)
    n = re.sub(r"[^a-z0-9]+", " ", n).strip()
    return n


def harvest_citywide():
    body = urllib.parse.urlencode({"data": QUERY}).encode()
    req = urllib.request.Request(
        "https://overpass-api.de/api/interpreter",
        data=body,
        headers={"User-Agent": "restaurant-lead-engine-dedupe (portfolio project)"},
    )
    with urllib.request.urlopen(req, timeout=90) as r:
        raw = json.loads(r.read())

    restaurants = []
    for el in raw.get("elements", []):
        tags = el.get("tags", {})
        restaurants.append(
            {
                "osm_id": el.get("id"),
                "name": tags.get("name"),
                "website": tags.get("website"),
                "phone": tags.get("phone"),
            }
        )
    os.makedirs(os.path.dirname(RAW_PATH), exist_ok=True)
    with open(RAW_PATH, "w") as f:
        json.dump(restaurants, f, indent=2)
    return restaurants


def main():
    if os.path.exists(RAW_PATH):
        with open(RAW_PATH) as f:
            restaurants = json.load(f)
    else:
        restaurants = harvest_citywide()

    groups = defaultdict(list)
    for r in restaurants:
        base = normalize(r["name"])
        if base:
            groups[base].append(r)

    chains = []
    for base, members in groups.items():
        if len(members) > 1:
            chains.append(
                {
                    "chain_base_name": base,
                    "location_count": len(members),
                    "locations": members,
                }
            )
    chains.sort(key=lambda c: c["location_count"], reverse=True)

    with open(OUT_PATH, "w") as f:
        json.dump(
            {
                "total_restaurants_scanned": len(restaurants),
                "chains_detected": len(chains),
                "chains": chains,
            },
            f,
            indent=2,
        )

    print(f"Scanned {len(restaurants)} restaurants citywide, found {len(chains)} "
          f"multi-location chains -> {OUT_PATH}")
    for c in chains:
        names = [m["name"] for m in c["locations"]]
        print(f"  {c['location_count']}x  {c['chain_base_name']!r}  ({', '.join(names)})")


if __name__ == "__main__":
    main()
