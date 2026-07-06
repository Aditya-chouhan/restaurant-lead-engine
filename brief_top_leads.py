"""
Stage 4 — brief: compose a rep pre-call brief for each of the top-scored
leads, using only facts detected in stage 2. No Claude/OpenAI API call is
made here (no key available in this environment, same constraint as the
July 2026 signal-engine-demo build) — the brief is template-composed
directly from the real detection evidence, and that's disclosed here and
on the write-up page rather than presented as a live model call.

Same honesty rule as account-brief-demo: if a category has no detection,
the brief says "no [category] detected" instead of inventing one.

Run it yourself: python3 brief_top_leads.py
"""

import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
IN_PATH = os.path.join(HERE, "data", "leads_scored.json")
OUT_DIR = os.path.join(HERE, "data", "briefs")

TOP_N = 3

CATEGORY_LABELS = {
    "ordering": "online ordering",
    "reservations": "reservations",
    "delivery_marketplace": "delivery marketplace",
    "voice_ai_competitor": "voice-AI product",
}


def line_for_category(category, detections):
    hits = [d for d in detections if d["category"] == category]
    label = CATEGORY_LABELS[category]
    if not hits:
        return f"- {label}: no {label} detected on the site"
    platforms = ", ".join(sorted({d["platform"] for d in hits}))
    evidence = ", ".join(sorted({d["evidence"] for d in hits}))
    return f"- {label}: {platforms} (evidence: `{evidence}`)"


def compose_brief(lead):
    lines = [
        f"# Pre-call brief — {lead['name']}",
        "",
        f"**Website:** {lead['website']}  ",
        f"**Phone:** {lead['phone']}  ",
        f"**Maple-fit score:** {lead['score']}",
        "",
        "## Why this account scored the way it did",
    ]
    lines += [f"- {reason}" for reason in lead["reasons"]] or ["- baseline, no scoring rules triggered"]
    lines += [
        "",
        "## Detected stack (from the restaurant's own site — every line cites its evidence)",
    ]
    lines += [line_for_category(cat, lead["detections"]) for cat in CATEGORY_LABELS]
    lines += [
        "",
        "## Talking point",
    ]
    if lead["score"] >= 60:
        lines.append(
            "High call-dependency, no direct ordering channel of their own — the exact "
            "profile of a restaurant losing orders to missed calls during peak hours."
        )
    elif any(d["category"] == "voice_ai_competitor" for d in lead["detections"]):
        lines.append(
            "A voice-AI product is already detected on this site — this is a displacement "
            "conversation, not a greenfield one. Lead with what's not working about the "
            "current setup, not with 'have you considered voice AI.'"
        )
    else:
        lines.append("Moderate fit — worth a call, not a priority-one account.")

    return "\n".join(lines) + "\n"


def main():
    with open(IN_PATH) as f:
        data = json.load(f)

    top = data["scored"][:TOP_N]
    os.makedirs(OUT_DIR, exist_ok=True)

    for lead in top:
        brief = compose_brief(lead)
        slug = lead["name"].lower().replace(" ", "-").replace("'", "").replace("’", "")
        path = os.path.join(OUT_DIR, f"{slug}.md")
        with open(path, "w") as f:
            f.write(brief)
        print(brief)
        print("---")

    print(f"Wrote {len(top)} briefs to {OUT_DIR}")


if __name__ == "__main__":
    main()
