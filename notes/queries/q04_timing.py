"""
Q04 — Two final verifications before locking the slice.

(a) Timing: when does 'disputed' actually open relative to 'signed' /
    'submitted'? If the dispute always opens *after* the sign-off, that
    proves the in-room 'OK' is theatrical and the morning email is when
    pain shows up.

(b) Distribution: are disputes concentrated by agency / agent / artist?
    If so, the pre-flight surface should weight specific relationships.

(c) For the marketing-recoup mystery: how many deals had a marketing
    recoup line in the SETTLEMENT (recoupsJson) but NOT mentioned in
    deal_notes_freetext? That's the "surprise at 2am" pattern.

Run from repo root:
    python notes/queries/q04_timing.py
"""
import sqlite3, os, json, re
DB = os.path.join(os.path.dirname(__file__), "..", "..", "data", "greenroom.db")
conn = sqlite3.connect(DB)
conn.row_factory = sqlite3.Row

def q(sql, *params):
    return [dict(r) for r in conn.execute(sql, params).fetchall()]

def section(title):
    print("\n" + "=" * 70)
    print(title)
    print("=" * 70)

# ---------- (a) Timing of disputes vs signoffs ----------
section("(a) Lag from signed/submitted to disputed (in hours)")
rows = q("""
    SELECT s.id, sh.date, a.name AS artist, s.signed_at, s.submitted_at,
           s.review_started_at, s.disputed_at, s.status
    FROM settlements s
    JOIN shows sh ON sh.id = s.show_id
    JOIN artists a ON a.id = sh.artist_id
    WHERE s.disputed_at IS NOT NULL
""")
print(f"Settlements with a disputed_at timestamp: {len(rows)}")
in_room = 0
next_morning = 0
later = 0
for r in rows:
    if r["disputed_at"] is None: continue
    anchor = r["signed_at"] or r["submitted_at"] or r["review_started_at"]
    if anchor is None:
        continue
    diff_h = (r["disputed_at"] - anchor) / 3600
    bucket = "in_room" if diff_h < 4 else ("next_morning" if diff_h < 36 else "later")
    if bucket == "in_room": in_room += 1
    elif bucket == "next_morning": next_morning += 1
    else: later += 1
    # uncomment to debug:
    # print(f"  {r['artist'][:25]:25}  anchor={anchor}  disputed_at={r['disputed_at']}  diff={diff_h:.1f}h  bucket={bucket}")
print(f"  In-room (<4h after signoff): {in_room}")
print(f"  Next morning (4–36h):         {next_morning}")
print(f"  Later (>36h):                 {later}")

# ---------- (b) Dispute concentration by agency / agent / artist ----------
section("(b) Dispute rate by agency")
rows = q("""
    SELECT ag.name AS agency,
           COUNT(*) AS shows,
           SUM(CASE WHEN s.status = 'disputed' THEN 1 ELSE 0 END) AS disputed,
           SUM(CASE WHEN s.status IN ('disputed','revised','finalized') THEN 1 ELSE 0 END) AS dispute_episodes
    FROM settlements s
    JOIN shows sh ON sh.id = s.show_id
    JOIN artists a ON a.id = sh.artist_id
    LEFT JOIN agents ag2 ON ag2.id = a.agent_id
    LEFT JOIN agencies ag ON ag.id = ag2.agency_id
    GROUP BY ag.name
    ORDER BY dispute_episodes DESC
""")
for r in rows:
    rate = 100*r["dispute_episodes"]/r["shows"] if r["shows"] else 0
    print(f"  {(r['agency'] or '<no agency>'):20}  shows={r['shows']:4}  disputed={r['disputed']:3}  dispute_episodes={r['dispute_episodes']:3}  rate={rate:.1f}%")

section("(b.2) Dispute rate by deal type (with denominators)")
rows = q("""
    SELECT d.deal_type,
           COUNT(*) AS shows,
           SUM(CASE WHEN s.status = 'disputed' THEN 1 ELSE 0 END) AS disputed,
           SUM(CASE WHEN s.status IN ('disputed','revised','finalized') THEN 1 ELSE 0 END) AS dispute_episodes
    FROM deals d
    JOIN settlements s ON s.show_id = d.show_id
    GROUP BY d.deal_type
    ORDER BY dispute_episodes DESC
""")
for r in rows:
    rate = 100*r["dispute_episodes"]/r["shows"] if r["shows"] else 0
    print(f"  {r['deal_type']:25} shows={r['shows']:4} disputed={r['disputed']:3}  episodes={r['dispute_episodes']:3}  rate={rate:.1f}%")

# ---------- (c) Marketing recoup in settlement but NOT in deal prose ----------
section("(c) Surprise recoup lines: in settlement, NOT mentioned in deal prose")
rows = q("""
    SELECT sh.date, a.name AS artist, d.deal_notes_freetext, s.status, s.recoups_json
    FROM settlements s
    JOIN shows sh ON sh.id = s.show_id
    JOIN artists a ON a.id = sh.artist_id
    JOIN deals d ON d.show_id = sh.id
    WHERE s.recoups_json IS NOT NULL AND s.recoups_json != '' AND s.recoups_json != '[]'
""")
surprise_count = 0
surprise_count_disputed_line = 0
patterns_by_category = {}
samples = []
for r in rows:
    try:
        recoups = json.loads(r["recoups_json"])
    except Exception:
        continue
    txt = (r["deal_notes_freetext"] or "").lower()
    for rcp in recoups:
        cat = rcp.get("category")
        # Did the deal email even hint at this kind of recoup?
        kw_map = {
            "marketing": ["marketing", "recoup", "ad spend", "promo spend"],
            "hospitality_overage": ["hospitality", "rider", "overage"],
            "production_overage": ["production", "tech rider", "overage"],
            "prior_advance": ["advance", "prior", "earlier"],
            "damages": ["damages", "damage"],
            "other": [],
        }
        kws = kw_map.get(cat, [])
        mentioned = any(k in txt for k in kws) if kws else False
        if not mentioned:
            surprise_count += 1
            patterns_by_category[cat] = patterns_by_category.get(cat, 0) + 1
            if rcp.get("status") == "disputed":
                surprise_count_disputed_line += 1
            if len(samples) < 8:
                samples.append((r["date"], r["artist"], cat, rcp.get("amount"), rcp.get("status"), txt[:160]))
print(f"  Recoup line items where the deal prose makes no mention of the category: {surprise_count}")
print(f"  Of those, recoup status='disputed': {surprise_count_disputed_line}")
print(f"  By category: {patterns_by_category}")
print(f"\n  Sample (date, artist, category, amount, status, prose snippet):")
for s in samples:
    print(f"    {s}")

# ---------- (d) Tier-ratchet / walkout patterns by agency ----------
section("(d) Complex-deal prose by agency (denominator = vs-deals)")
rows = q("""
    SELECT ag.name AS agency, d.deal_notes_freetext
    FROM deals d
    JOIN shows sh ON sh.id = d.show_id
    JOIN artists a ON a.id = sh.artist_id
    LEFT JOIN agents ag2 ON ag2.id = a.agent_id
    LEFT JOIN agencies ag ON ag.id = ag2.agency_id
    WHERE d.deal_type = 'vs'
""")
by_agency = {}
for r in rows:
    txt = (r["deal_notes_freetext"] or "")
    complex = bool(re.search(r"ratchet|walkout|escalat|tier|sliding", txt, re.IGNORECASE))
    by_agency.setdefault(r["agency"] or "<none>", [0,0])
    by_agency[r["agency"] or "<none>"][0] += 1
    if complex:
        by_agency[r["agency"] or "<none>"][1] += 1
for k, (total, complex) in sorted(by_agency.items(), key=lambda x: -x[1][1]):
    rate = 100*complex/total if total else 0
    print(f"  {k:20}  vs-deals={total:4}  complex_prose={complex:3}  rate={rate:.0f}%")
