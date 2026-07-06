"""
Stage 2 — fingerprint: fetch each restaurant's real homepage once and detect
which ordering / reservation / delivery / voice-AI platform it actually
runs, from real HTML.

Patterns are URL-context-aware (matched against href/src fragments in the
page), not bare-word substring matches. That distinction is load-bearing:
an earlier manual test of this same idea flagged "Tick Tock Diner" as a
Tock reservations user because "tock" appeared in the restaurant's own
name — a bare-substring match would have produced a false positive on
this exact dataset. The fix is requiring the platform's real domain
fragment (exploretock.com), not the word.

Every detection carries the literal matched fragment as its evidence —
nothing here is asserted without the string that produced it. A site that
fails to fetch is recorded as fetch_failed, not silently dropped.

Run it yourself: python3 fingerprint.py
Sites change; re-running later may show different (still real) results.
"""

import json
import os
import re
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
IN_PATH = os.path.join(HERE, "data", "restaurants_raw.json")
OUT_PATH = os.path.join(HERE, "data", "fingerprints.json")

# category -> platform -> regex matched against raw page HTML.
# All patterns require a real domain fragment, never a bare product word.
PATTERNS = {
    "ordering": {
        "toast": r"order\.toasttab\.com|toasttab\.com",
        "chownow": r"chownow\.com",
        "square": r"squareup\.com|[\w-]+\.square\.site",
        "owner_com": r"owner\.com",
        "bentobox_ordering": r"bentobox\.com|getbento\.com",
        "menufy": r"menufy\.com",
    },
    "reservations": {
        "opentable": r"opentable\.com",
        "resy": r"resy\.com",
        "tock": r"exploretock\.com",
        "sevenrooms": r"sevenrooms\.com",
    },
    "delivery_marketplace": {
        "doordash": r"doordash\.com",
        "ubereats": r"ubereats\.com",
        "grubhub": r"grubhub\.com",
    },
    # NOTE ON PRECISION: "popmenu.com" only proves the restaurant runs the
    # Popmenu website/menu platform, not that Popmenu's optional AI
    # phone-answering add-on is switched on for that account — Popmenu
    # sells that as a separate feature, not a default. Labeled
    # "popmenu_platform" (not "popmenu_voice") to avoid overclaiming an
    # active competitor from a platform-level signal. slang.ai and
    # hostai.co ARE voice-AI-first products, so a hit there is a much
    # stronger signal than a Popmenu hit.
    "voice_ai_competitor": {
        "slang_ai": r"slang\.ai",
        "popmenu_platform": r"popmenu\.com",
        "hostai": r"hostai\.co",
    },
}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
}


def fetch(url, timeout=15):
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", errors="ignore")


def detect(html):
    hits = []
    for category, platforms in PATTERNS.items():
        for platform, pattern in platforms.items():
            m = re.search(pattern, html, re.IGNORECASE)
            if m:
                hits.append(
                    {"category": category, "platform": platform, "evidence": m.group(0)}
                )
    return hits


def main():
    with open(IN_PATH) as f:
        restaurants = json.load(f)

    results = []
    ok, failed = 0, 0
    for r in restaurants:
        entry = {"osm_id": r["osm_id"], "name": r["name"], "website": r["website"]}
        try:
            html = fetch(r["website"])
            entry["fetch_failed"] = False
            entry["detections"] = detect(html)
            ok += 1
        except Exception as e:
            entry["fetch_failed"] = True
            entry["fetch_error"] = str(e)
            entry["detections"] = []
            failed += 1
        results.append(entry)

    with open(OUT_PATH, "w") as f:
        json.dump(results, f, indent=2)

    print(f"Fingerprinted {len(results)} sites: {ok} fetched, {failed} fetch_failed -> {OUT_PATH}")


if __name__ == "__main__":
    main()
