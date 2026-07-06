"""
Stage 3 — score: rank fingerprinted restaurants by fit for a voice-AI phone
agent, using only detected facts from stage 2. Weights are fully disclosed
below — nothing hidden, nothing tuned after the fact to make a nicer story.

The logic:
  +40  phone listed, no online-ordering platform detected
       -> the restaurant is call-dependent for orders/reservations, which
       is exactly the missed-call pain a phone-answering AI sells against
       (industry data: restaurants miss 21-43% of calls at peak, an
       estimated $100-600/day in lost orders per location).
  +25  has an OpenTable integration
       -> OpenTable is a real, live Maple integration (per Maple's own
       announced partnership). A restaurant already on OpenTable has
       lower activation friction for a Maple-style agent than one with no
       reservation platform at all.
  +15  has delivery-marketplace links (DoorDash/UberEats/Grubhub) but no
       direct ordering platform
       -> already paying 15-30% marketplace commissions with no owned
       ordering channel; the phone is likely still the only direct path,
       same call-dependency logic as the +40 rule, at lower confidence.
  -50  voice-AI competitor detected (Slang.ai, Popmenu voice, HostAI)
       -> this is a takeover/displacement sale, not a greenfield one.
       Scored down, not excluded, and not hidden — an account team may
       still want it, just not first.
  +0   baseline otherwise.
Fetch-failed sites are excluded from the ranking (no evidence to score
against) and reported separately, not silently dropped.

Run it yourself: python3 score_leads.py
"""

import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
RESTAURANTS_PATH = os.path.join(HERE, "data", "restaurants_raw.json")
FINGERPRINTS_PATH = os.path.join(HERE, "data", "fingerprints.json")
OUT_PATH = os.path.join(HERE, "data", "leads_scored.json")

ORDERING_PLATFORMS = {"toast", "chownow", "square", "owner_com", "bentobox_ordering", "menufy"}
DELIVERY_PLATFORMS = {"doordash", "ubereats", "grubhub"}
VOICE_AI_PLATFORMS = {"slang_ai", "popmenu_platform", "hostai"}


def score(entry, phone):
    categories = {d["category"] for d in entry["detections"]}
    platforms = {d["platform"] for d in entry["detections"]}

    reasons = []
    total = 0

    has_ordering = bool(platforms & ORDERING_PLATFORMS)
    has_delivery = "delivery_marketplace" in categories
    has_opentable = "opentable" in platforms
    has_voice_competitor = bool(platforms & VOICE_AI_PLATFORMS)

    if phone and not has_ordering:
        total += 40
        reasons.append("+40 phone listed, no online ordering detected (call-dependent)")

    if has_opentable:
        total += 25
        reasons.append("+25 OpenTable detected (live Maple integration = lower activation friction)")

    if has_delivery and not has_ordering:
        total += 15
        reasons.append("+15 delivery marketplace present, no direct ordering channel")

    if has_voice_competitor:
        total -= 50
        reasons.append(
            "-50 voice-AI-adjacent platform detected (Slang.ai/HostAI = confirmed voice-AI "
            "competitor; Popmenu = platform-level signal only, feature may not be active)"
        )

    return total, reasons


def main():
    with open(RESTAURANTS_PATH) as f:
        restaurants = {r["osm_id"]: r for r in json.load(f)}
    with open(FINGERPRINTS_PATH) as f:
        fingerprints = json.load(f)

    scored, excluded = [], []
    for fp in fingerprints:
        r = restaurants[fp["osm_id"]]
        if fp["fetch_failed"]:
            excluded.append({"name": r["name"], "website": r["website"], "reason": "fetch_failed"})
            continue
        total, reasons = score(fp, r["phone"])
        scored.append(
            {
                "osm_id": fp["osm_id"],
                "name": r["name"],
                "website": r["website"],
                "phone": r["phone"],
                "score": total,
                "reasons": reasons,
                "detections": fp["detections"],
            }
        )

    scored.sort(key=lambda x: x["score"], reverse=True)

    with open(OUT_PATH, "w") as f:
        json.dump({"scored": scored, "excluded": excluded}, f, indent=2)

    print(f"Scored {len(scored)} leads, excluded {len(excluded)} (fetch_failed) -> {OUT_PATH}")
    print()
    print(f"{'name':<28} {'score':>5}  reasons")
    for lead in scored[:15]:
        print(f"{lead['name'][:28]:<28} {lead['score']:>5}  {'; '.join(lead['reasons']) or 'baseline'}")


if __name__ == "__main__":
    main()
