"""
Stage 1 — harvest: pull a real set of NYC restaurants from OpenStreetMap.

The GTM problem this pipeline attacks: a voice-AI-for-restaurants company
scaling an SMB sales team needs a constant feed of prioritized restaurant
accounts — "the pipes that feed leads in." This stage is the top of that
pipe: real restaurants, with real websites and real phone numbers, from a
fully public source that requires no API key.

Data source: the Overpass API over OpenStreetMap. One query, one bounding
box in Manhattan, capped result size, identifying User-Agent — inside
Overpass's usage policy. The raw response is saved to
data/restaurants_raw.json so the later stages (and anyone reviewing this)
never need to re-hit the API: downstream stages are pure functions of the
captured snapshot.

Run it yourself: python3 harvest.py
Re-running will re-query OSM, so the restaurant set can drift as OSM is
edited — that's real data behaving like real data, not a bug.
"""

import json
import os
import urllib.parse
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
OUT_PATH = os.path.join(HERE, "data", "restaurants_raw.json")

# One bounding box in lower/mid Manhattan — Maple's home city.
# (south, west, north, east)
BBOX = "40.72,-74.01,40.76,-73.97"
MAX_RESULTS = 80

QUERY = f"""
[out:json][timeout:50];
node["amenity"="restaurant"]["website"]["phone"]({BBOX});
out body {MAX_RESULTS};
"""


def main():
    body = urllib.parse.urlencode({"data": QUERY}).encode()
    req = urllib.request.Request(
        "https://overpass-api.de/api/interpreter",
        data=body,
        headers={"User-Agent": "restaurant-lead-engine-demo (portfolio project)"},
    )
    with urllib.request.urlopen(req, timeout=60) as r:
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
                "cuisine": tags.get("cuisine"),
                "opening_hours": tags.get("opening_hours"),
            }
        )

    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    with open(OUT_PATH, "w") as f:
        json.dump(restaurants, f, indent=2)

    with_site = sum(1 for r in restaurants if r["website"])
    print(f"Harvested {len(restaurants)} restaurants ({with_site} with websites) "
          f"from bbox {BBOX} -> {OUT_PATH}")


if __name__ == "__main__":
    main()
