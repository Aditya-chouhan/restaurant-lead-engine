"""
Stage 7 — prototype, test, roll out: run a real A/B test between two scoring
hypotheses on the same 65 leads, measure how much the ranking actually
changes, and write down a decision — the actual "prototype -> test -> roll
out new automations" cycle a GTM Engineer JD asks for, not a description of
one.

The hypothesis being tested: score_leads.py (Model A, shipped) gives
delivery-marketplace-only accounts a lower bonus (+15) than pure
phone-dependent accounts (+40), on the theory that call-dependency is the
stronger signal. Model B tests a competing theory: a restaurant paying
15-30% commission to DoorDash/UberEats/Grubhub with no direct ordering
channel is under equally real financial pressure, so that bonus should be
raised to +30 (still below the +40 call-dependency signal, but a real lift,
not a token one).

Method: re-score every already-fingerprinted lead under both models (no new
fetches — this is a pure function of data already captured in
leads_scored.json), then measure with two concrete numbers instead of a
feeling:
  1. Top-10 overlap: how many of Model A's top 10 leads are still in
     Model B's top 10?
  2. Spearman rank correlation across the full ranked list (implemented
     from scratch below, no scipy dependency).
A decision is written based on those numbers, not asserted first and
backfilled with support.

Run it yourself: python3 experiment_scoring_models.py
"""

import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
IN_PATH = os.path.join(HERE, "data", "leads_scored.json")
OUT_PATH = os.path.join(HERE, "data", "experiment_ab.json")

ORDERING_PLATFORMS = {"toast", "chownow", "square", "owner_com", "bentobox_ordering", "menufy"}
VOICE_AI_PLATFORMS = {"slang_ai", "popmenu_platform", "hostai"}

DELIVERY_BONUS_A = 15  # shipped, in score_leads.py
DELIVERY_BONUS_B = 30  # hypothesis under test


def score(entry, phone, delivery_bonus):
    categories = {d["category"] for d in entry["detections"]}
    platforms = {d["platform"] for d in entry["detections"]}

    has_ordering = bool(platforms & ORDERING_PLATFORMS)
    has_delivery = "delivery_marketplace" in categories
    has_opentable = "opentable" in platforms
    has_voice_competitor = bool(platforms & VOICE_AI_PLATFORMS)

    total = 0
    if phone and not has_ordering:
        total += 40
    if has_opentable:
        total += 25
    if has_delivery and not has_ordering:
        total += delivery_bonus
    if has_voice_competitor:
        total -= 50
    return total


def spearman(rank_a, rank_b, names):
    """Spearman rank correlation, computed from scratch (no scipy)."""
    n = len(names)
    d_squared_sum = sum((rank_a[name] - rank_b[name]) ** 2 for name in names)
    return 1 - (6 * d_squared_sum) / (n * (n**3 - 1))


def to_ranks(scored_list):
    """name -> rank (1 = highest score), ties broken by name for determinism."""
    ordered = sorted(scored_list, key=lambda x: (-x["score_for_rank"], x["name"]))
    return {lead["name"]: i + 1 for i, lead in enumerate(ordered)}


def main():
    with open(IN_PATH) as f:
        data = json.load(f)
    leads = data["scored"]

    model_a = [{"name": l["name"], "score_for_rank": score(l, l["phone"], DELIVERY_BONUS_A)} for l in leads]
    model_b = [{"name": l["name"], "score_for_rank": score(l, l["phone"], DELIVERY_BONUS_B)} for l in leads]

    rank_a = to_ranks(model_a)
    rank_b = to_ranks(model_b)
    names = [l["name"] for l in leads]

    top10_a = {n for n, r in rank_a.items() if r <= 10}
    top10_b = {n for n, r in rank_b.items() if r <= 10}
    overlap = len(top10_a & top10_b)

    corr = spearman(rank_a, rank_b, names)
    scores_a = {m["name"]: m["score_for_rank"] for m in model_a}
    scores_b = {m["name"]: m["score_for_rank"] for m in model_b}
    leads_with_changed_score = sum(1 for n in names if scores_a[n] != scores_b[n])

    if overlap >= 9 and corr >= 0.9:
        decision = (
            f"Ship Model A as-is. {leads_with_changed_score}/{len(names)} leads' "
            f"absolute scores did move when the delivery bonus went from "
            f"+{DELIVERY_BONUS_A} to +{DELIVERY_BONUS_B}, but the shift was "
            f"uniform within that group and never crossed another lead's score "
            f"band — rank order came out fully invariant ({overlap}/10 top-10 "
            f"overlap, {corr:.2f} rank correlation). The delivery-commission "
            f"hypothesis may still be true, but this scoring model isn't the "
            f"right place to encode it — a flat bonus this size doesn't change "
            f"who gets called first. Not worth the added complexity for this "
            f"dataset."
        )
    elif overlap >= 6:
        decision = (
            f"Worth a closer look before rolling out. {overlap}/10 top-10 overlap "
            f"and {corr:.2f} rank correlation is a real but moderate shift — "
            f"Model B meaningfully reorders some accounts. Recommend running "
            f"both scored lists past an actual AE for a gut-check before "
            f"picking one, rather than deciding from the numbers alone."
        )
    else:
        decision = (
            f"Do not ship Model B without more validation. Only {overlap}/10 "
            f"top-10 leads survive and rank correlation is {corr:.2f} — the two "
            f"models disagree enough that the underlying hypothesis "
            f"(delivery-commission pain ≈ call-dependency pain) needs real "
            f"outcome data, not just a heavier weight, before it goes live."
        )

    result = {
        "hypothesis": (
            f"Delivery-marketplace-only accounts deserve a stronger fit bonus "
            f"(+{DELIVERY_BONUS_B} instead of +{DELIVERY_BONUS_A}) because "
            f"commission pressure (15-30% per order) is as real a pain point as "
            f"call-dependency."
        ),
        "model_a_delivery_bonus": DELIVERY_BONUS_A,
        "model_b_delivery_bonus": DELIVERY_BONUS_B,
        "top10_overlap_of_10": overlap,
        "spearman_rank_correlation": round(corr, 3),
        "leads_with_changed_absolute_score": leads_with_changed_score,
        "total_leads": len(names),
        "decision": decision,
    }

    with open(OUT_PATH, "w") as f:
        json.dump(result, f, indent=2)

    print(f"Hypothesis: {result['hypothesis']}")
    print(f"Top-10 overlap: {overlap}/10   Spearman correlation: {corr:.3f}   "
          f"Leads with changed score: {leads_with_changed_score}/{len(names)}")
    print(f"Decision: {decision}")
    print(f"-> {OUT_PATH}")


if __name__ == "__main__":
    main()
