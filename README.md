# Restaurant Lead Engine — public demo

A GTM lead-sourcing pipeline for a voice-AI-for-restaurants company: harvest
real restaurants, fingerprint their real websites for ordering/reservation/
delivery/voice-AI stack, score them for fit, and generate rep-ready pre-call
briefs — all four stages, no API keys, on real public data.

**Write-up:** https://aditya-chouhan.github.io/restaurant-lead-engine/

## Why this, specifically

Maple (voice AI for restaurants) is hiring a GTM Engineer whose first listed
responsibility is "build and automate pipelines that close loops from the
top of the funnel." They're simultaneously hiring SMB AEs and BDRs and have
stated a target of 40,000 customers from ~2,500 today — that's a sales team
that needs a constant, prioritized feed of real accounts, which is exactly
what this pipeline is. Maple's own public GTM (POS/OpenTable partnerships,
missed-call cost data) is the motivating case throughout — this project is
not built or branded as Maple's, it's built around the problem their own
job posting describes.

## Run it yourself

```
python3 harvest.py
python3 fingerprint.py
python3 score_leads.py
python3 brief_top_leads.py
python3 dedupe_chains.py
python3 build_dashboard.py
python3 experiment_scoring_models.py
```

No API keys, no dependencies beyond the Python standard library.

## What's in it

- `harvest.py` — pulls real NYC restaurants (name, website, phone) from the
  Overpass API over OpenStreetMap. No key required.
- `fingerprint.py` — fetches each restaurant's real homepage once and
  detects ordering / reservation / delivery / voice-AI platforms via
  URL-context-aware pattern matching (not bare-word matching — see below).
- `score_leads.py` — a disclosed, fully-documented composite score for fit
  as a Maple-style voice-AI account.
- `brief_top_leads.py` — composes a rep pre-call brief for the top 3 scored
  leads, using only detected facts, each with its evidence.
- `dedupe_chains.py` — a separate, wider citywide query (documented reason
  in the file: chain detection needs more data than the 80-restaurant demo
  sample) that detects real multi-location chains so they collapse into one
  account instead of N unrelated leads. Found 5 real chains in a
  400-restaurant citywide sample: 5 Napkin Burger, Pio Pio, IHOP, Carmine's,
  Dallas BBQ — each a genuinely distinct location (different phone,
  different address-specific website URL), not a data artifact.
- `build_dashboard.py` — generates `rep_dashboard.html`, a single
  self-contained, sortable/searchable static page an AE would actually
  open, instead of reading JSON or markdown files directly.
- `experiment_scoring_models.py` — a real A/B test between two scoring
  hypotheses on the same 65 leads (no new data, pure re-scoring), measured
  with top-10 overlap and Spearman rank correlation, ending in a written
  decision. Result: raising the delivery-marketplace bonus from +15 to +30
  changed 6/65 leads' absolute scores but zero rank order (10/10 top-10
  overlap, 1.00 correlation) — a concrete "prototype, test, decide" cycle,
  not a description of one.
- `data/` — the real captured output of each stage.

## The precision lesson, found twice while building this

An early manual test (a plain `grep` across restaurant homepages, done
while scoping this project) flagged two false positives:

1. **"Tick Tock Diner"** matched a bare-word search for `tock` — because
   the restaurant's own name contains the string, not because it uses Tock
   reservations. It actually uses OpenTable.
2. **samsunnynyc.com** also matched bare `tock` — not from anything
   reservation-related, but from a JS config string,
   `"stores.EnableOutOfStockAlignment"` — the substring `tock` inside
   "InStock"/"OutOfStock".

`fingerprint.py` requires the platform's real domain fragment
(`exploretock.com`, not `tock`) specifically because of these two, and both
are verified clean in the current output — a small, concrete argument for
why signal detection needs to match evidence, not keywords.

**Scale note:** 80 restaurants, one Manhattan bounding box, homepage-only
fingerprinting (a restaurant whose ordering link lives on a subpage won't
be detected). This demonstrates the pipeline architecture and the
precision discipline, not a production-scale account universe. The obvious
next upgrade — Google Places/Yelp enrichment for review counts and hours —
needs a billed API key and isn't included here.
