"""
Stage 6 — rep tooling: generate a single static HTML page an AE would
actually open, instead of asking them to read JSON or markdown files.

This is the "rep tooling layer that makes an AE genuinely faster" half of
the JD, applied to this pipeline's own output: sortable by score, searchable
by name, every row shows its scoring reasons and detected stack inline, and
the 3 leads with a full generated brief (see brief_top_leads.py) expand to
show it without leaving the page.

No server, no framework, no build step — one self-contained HTML file with
the real scored-lead data embedded as JSON and ~40 lines of vanilla JS for
sort/search/expand. That's a deliberate choice: an AE should be able to
open this file locally with zero setup.

Run it yourself: python3 build_dashboard.py
"""

import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
LEADS_PATH = os.path.join(HERE, "data", "leads_scored.json")
BRIEFS_DIR = os.path.join(HERE, "data", "briefs")
OUT_PATH = os.path.join(HERE, "rep_dashboard.html")

CATEGORY_LABELS = {
    "ordering": "ordering",
    "reservations": "reservations",
    "delivery_marketplace": "delivery",
    "voice_ai_competitor": "voice-AI-adjacent",
}


def slug(name):
    return name.lower().replace(" ", "-").replace("'", "").replace("’", "")


def load_brief(name):
    path = os.path.join(BRIEFS_DIR, f"{slug(name)}.md")
    if os.path.exists(path):
        with open(path) as f:
            return f.read()
    return None


def stack_summary(detections):
    by_cat = {}
    for d in detections:
        by_cat.setdefault(d["category"], []).append(d["platform"])
    if not by_cat:
        return "no platforms detected"
    return "; ".join(f"{CATEGORY_LABELS.get(c, c)}: {', '.join(sorted(set(p)))}" for c, p in by_cat.items())


def main():
    with open(LEADS_PATH) as f:
        data = json.load(f)

    rows = []
    for lead in data["scored"]:
        rows.append(
            {
                "name": lead["name"],
                "score": lead["score"],
                "website": lead["website"],
                "phone": lead["phone"],
                "reasons": lead["reasons"] or ["baseline, no scoring rules triggered"],
                "stack": stack_summary(lead["detections"]),
                "brief": load_brief(lead["name"]),
            }
        )

    html = HTML_TEMPLATE.replace("__DATA__", json.dumps(rows))
    with open(OUT_PATH, "w") as f:
        f.write(html)

    with_brief = sum(1 for r in rows if r["brief"])
    print(f"Built dashboard with {len(rows)} leads ({with_brief} with a full brief) -> {OUT_PATH}")


HTML_TEMPLATE = """<!doctype html>
<title>Rep Dashboard — Restaurant Lead Engine</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
  :root { --paper:#ECEEEB; --paper-raised:#F5F6F3; --ink:#191D1B; --ink-soft:#4B524D; --ink-faint:#7B8179; --line:#D6D3C8; --accent:#A8641F; --accent-soft:#EADFCB; }
  * { box-sizing: border-box; }
  body { margin:0; background:var(--paper); color:var(--ink); font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif; font-size:15px; }
  .wrap { max-width:960px; margin:0 auto; padding:32px 20px 80px; }
  h1 { font-size:22px; margin:0 0 6px; }
  .sub { color:var(--ink-faint); font-size:13.5px; margin:0 0 24px; }
  .controls { display:flex; gap:10px; margin-bottom:18px; flex-wrap:wrap; }
  input[type=search] { flex:1; min-width:220px; padding:9px 12px; border:1px solid var(--line); border-radius:7px; font-size:14px; background:var(--paper-raised); color:var(--ink); }
  select { padding:9px 12px; border:1px solid var(--line); border-radius:7px; font-size:14px; background:var(--paper-raised); color:var(--ink); }
  table { width:100%; border-collapse:collapse; background:var(--paper-raised); border:1px solid var(--line); border-radius:10px; overflow:hidden; }
  th, td { text-align:left; padding:10px 14px; border-bottom:1px solid var(--line); font-size:13.5px; vertical-align:top; }
  th { background:var(--paper); color:var(--ink-faint); text-transform:uppercase; font-size:10.5px; letter-spacing:.04em; cursor:pointer; user-select:none; }
  tr:last-child td { border-bottom:none; }
  tr.lead-row:hover { background:var(--accent-soft); cursor:pointer; }
  .score { font-weight:700; font-family:ui-monospace,monospace; }
  .reasons { color:var(--ink-soft); font-size:12.5px; }
  .stack { color:var(--ink-faint); font-size:12px; font-family:ui-monospace,monospace; }
  .brief-row td { background:#14181A; color:#E4E7E2; font-family:ui-monospace,monospace; font-size:12.5px; white-space:pre-wrap; padding:16px 18px; }
  .badge { display:inline-block; font-size:10.5px; font-family:ui-monospace,monospace; padding:2px 7px; border-radius:10px; background:var(--accent-soft); color:var(--accent); margin-left:6px; }
  .hidden { display:none; }
  .count { color:var(--ink-faint); font-size:12.5px; margin-bottom:10px; }
</style>
<div class="wrap">
  <h1>Rep Dashboard — Restaurant Lead Engine</h1>
  <p class="sub">Real leads, real detected stack, real scoring reasons. Click a row to expand its full pre-call brief where one exists.</p>
  <div class="controls">
    <input type="search" id="search" placeholder="Search by restaurant name...">
    <select id="sortSel">
      <option value="score_desc">Sort: score (high to low)</option>
      <option value="score_asc">Sort: score (low to high)</option>
      <option value="name_asc">Sort: name (A-Z)</option>
    </select>
  </div>
  <div class="count" id="count"></div>
  <table>
    <thead><tr><th>restaurant</th><th>score</th><th>detected stack</th><th>phone</th></tr></thead>
    <tbody id="tbody"></tbody>
  </table>
</div>
<script>
  var DATA = __DATA__;

  function render() {
    var q = document.getElementById('search').value.toLowerCase();
    var sortMode = document.getElementById('sortSel').value;
    var rows = DATA.filter(function(r){ return r.name.toLowerCase().indexOf(q) !== -1; });
    rows.sort(function(a,b){
      if (sortMode === 'score_desc') return b.score - a.score;
      if (sortMode === 'score_asc') return a.score - b.score;
      return a.name.localeCompare(b.name);
    });
    document.getElementById('count').textContent = rows.length + ' of ' + DATA.length + ' leads';
    var tbody = document.getElementById('tbody');
    tbody.innerHTML = '';
    rows.forEach(function(r, i){
      var tr = document.createElement('tr');
      tr.className = 'lead-row';
      tr.innerHTML = '<td>' + r.name + (r.brief ? '<span class="badge">full brief</span>' : '') +
        '<div class="reasons">' + r.reasons.join(' · ') + '</div></td>' +
        '<td class="score">' + r.score + '</td>' +
        '<td class="stack">' + r.stack + '</td>' +
        '<td>' + (r.phone || '') + '</td>';
      var briefTr = document.createElement('tr');
      briefTr.className = 'brief-row hidden';
      var td = document.createElement('td');
      td.colSpan = 4;
      td.textContent = r.brief || 'No full brief generated for this lead (only the top-scored leads get one — see brief_top_leads.py).';
      briefTr.appendChild(td);
      tr.addEventListener('click', function(){ briefTr.classList.toggle('hidden'); });
      tbody.appendChild(tr);
      tbody.appendChild(briefTr);
    });
  }

  document.getElementById('search').addEventListener('input', render);
  document.getElementById('sortSel').addEventListener('change', render);
  render();
</script>
"""

if __name__ == "__main__":
    main()
