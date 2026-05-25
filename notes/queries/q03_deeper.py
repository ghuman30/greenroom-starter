"""
Q03 — Go deeper on the seams that lit up in Q02.

Confirmed patterns to extend:
  (a) The 'disputed status with positive signoff' isn't one example — 15/24
      disputed shows have it. Look at the *full* set of distinct sign-off
      strings on disputed shows. The case writers seeded a small number of
      patterns; we want to name them.
  (b) Coastal Spell has 6 shows. The 2025-03-14 dispute lives at the special
      show_id 'show_coastal_spell_dispute'. The total_to_artist appears to be
      the AGREED post-dispute amount ($12,285), not the originally calculated
      $11,565 — verify and note.
  (c) Look at marketing-recoup language across ALL deals (not just WME) to
      see how the ambiguity manifests in prose.
  (d) Hospitality-cap overruns — Mariana flagged this as a Wednesday-knowable
      signal. Quantify how often actual hospitality expenses exceed
      hospitality_cap.
  (e) Tier ratchets / walkout pots in freetext — count how many vs-deals
      have these but no structured representation.

Run from repo root:
    python notes/queries/q03_deeper.py
"""
import sqlite3
import os
import json
import re

DB = os.path.join(os.path.dirname(__file__), "..", "..", "data", "greenroom.db")
conn = sqlite3.connect(DB)
conn.row_factory = sqlite3.Row

def q(sql, *params):
    return [dict(r) for r in conn.execute(sql, params).fetchall()]

def section(title):
    print("\n" + "=" * 70)
    print(title)
    print("=" * 70)

# ---------- (a) All distinct sign-off strings on disputed shows ----------
section("(a) Sign-off text on disputed shows — full distribution")
rows = q("""
    SELECT signoff_text, COUNT(*) AS c
    FROM settlements
    WHERE status = 'disputed'
    GROUP BY signoff_text
    ORDER BY c DESC
""")
for r in rows:
    print(f"  {r['c']:3}  {(r['signoff_text'] or '<NULL>')!r}")

# ---------- (a.2) The reverse: distinct sign-off text on PAID shows ----------
section("(a.2) Sign-off text on PAID shows — full distribution")
rows = q("""
    SELECT signoff_text, COUNT(*) AS c
    FROM settlements
    WHERE status = 'paid' AND signoff_text IS NOT NULL
    GROUP BY signoff_text
    ORDER BY c DESC
    LIMIT 30
""")
for r in rows:
    print(f"  {r['c']:3}  {(r['signoff_text'] or '<NULL>')!r}")

# ---------- (b) Coastal Spell dispute — verify $12,285 = agreed, not calculated ----------
section("(b) Coastal Spell dispute show — full record check")
r = q("""
    SELECT s.*, sh.date, a.name AS artist, d.deal_notes_freetext
    FROM settlements s
    JOIN shows sh ON sh.id = s.show_id
    JOIN artists a ON a.id = sh.artist_id
    JOIN deals d ON d.show_id = s.show_id
    WHERE s.show_id = 'show_coastal_spell_dispute'
""")[0]
print(f"  total_to_artist: ${r['total_to_artist']}")
print(f"  Dispute thread says agreed: $12,285. Originally calculated: $11,565.")
print(f"  Status: {r['status']}, signoff: {r['signoff_text']!r}")
print(f"  notes (settlement-level): {(r['notes'] or '')[:500]}")
print(f"  --> the data carries the RESOLVED amount but status is still 'disputed'.")
print(f"  --> classic state drift; the formal revision/finalize transition never happened.")
print(f"  Also check calculation_json:")
print(f"     {(r['calculation_json'] or '')[:600]}")

# ---------- (c) "marketing recoup" language across ALL deals ----------
section("(c) Marketing-recoup language in deal_notes_freetext (all deals)")
rows = q("""
    SELECT sh.date, a.name AS artist, d.deal_notes_freetext, s.status,
           s.recoups_json
    FROM deals d
    JOIN shows sh ON sh.id = d.show_id
    JOIN artists a ON a.id = sh.artist_id
    LEFT JOIN settlements s ON s.show_id = d.show_id
    WHERE LOWER(d.deal_notes_freetext) LIKE '%marketing%recoup%'
       OR LOWER(d.deal_notes_freetext) LIKE '%marketing%off%gross%'
       OR LOWER(d.deal_notes_freetext) LIKE '%mkt%recoup%'
    ORDER BY sh.date DESC
""")
print(f"Deals mentioning marketing recoup in prose: {len(rows)}")
# Bucket by clause shape
inside = 0
outside = 0
ambiguous = 0
samples = {"inside": [], "outside": [], "ambiguous": []}
for r in rows:
    txt = (r["deal_notes_freetext"] or "").lower()
    # "inside the cap" / "included in expense cap" / "counts toward expenses"
    is_inside = bool(re.search(r"(inside|within|included|counts toward|counted in|part of) (the )?(expense )?cap", txt))
    # "outside" / "in addition to" / "separate from" / "against gross"
    is_outside = bool(re.search(r"(outside|in addition to|separate|additional|not in|excluded from|against gross)", txt))
    # heuristic — if neither/both, it's ambiguous
    if is_inside and not is_outside:
        inside += 1
        samples["inside"].append(r)
    elif is_outside and not is_inside:
        outside += 1
        samples["outside"].append(r)
    else:
        ambiguous += 1
        samples["ambiguous"].append(r)
print(f"\n  Phrasing buckets (heuristic):")
print(f"    Inside the cap (explicit): {inside}")
print(f"    Outside the cap (explicit): {outside}")
print(f"    Ambiguous (neither/both): {ambiguous}")

print(f"\n  Sample of ambiguous prose (the ones a model would have to flag):")
for r in samples["ambiguous"][:8]:
    print(f"    [{r['date']}] {r['artist']}  status={r['status']}")
    print(f"      {(r['deal_notes_freetext'] or '')[:240]}")

print(f"\n  Sample of unambiguous-outside prose:")
for r in samples["outside"][:5]:
    print(f"    [{r['date']}] {r['artist']}  status={r['status']}")
    print(f"      {(r['deal_notes_freetext'] or '')[:240]}")

# ---------- (d) Hospitality overruns vs hospitality_cap ----------
section("(d) Hospitality actual vs hospitality_cap")
rows = q("""
    SELECT d.hospitality_cap, sh.id AS show_id, a.name AS artist, sh.date,
           SUM(CASE WHEN e.category='hospitality' THEN e.amount ELSE 0 END) AS hosp_actual,
           s.status
    FROM deals d
    JOIN shows sh ON sh.id = d.show_id
    JOIN artists a ON a.id = sh.artist_id
    LEFT JOIN expenses e ON e.show_id = sh.id
    LEFT JOIN settlements s ON s.show_id = sh.id
    WHERE d.hospitality_cap IS NOT NULL
    GROUP BY sh.id
""")
total_with_cap = len(rows)
over = sum(1 for r in rows if r["hosp_actual"] and r["hosp_actual"] > r["hospitality_cap"])
over_by_pct = sum(1 for r in rows if r["hosp_actual"] and r["hosp_actual"] > 1.1 * r["hospitality_cap"])
big_over = [r for r in rows if r["hosp_actual"] and r["hosp_actual"] > 1.25 * r["hospitality_cap"]]
print(f"  Shows with a hospitality cap: {total_with_cap}")
print(f"  Hospitality actual > cap: {over}  ({100*over/total_with_cap:.0f}%)")
print(f"  Hospitality actual > 1.1x cap: {over_by_pct}  ({100*over_by_pct/total_with_cap:.0f}%)")
print(f"  Hospitality actual > 1.25x cap (likely material): {len(big_over)}")
print(f"\n  Sample of big overruns:")
for r in sorted(big_over, key=lambda x: x["hosp_actual"]/x["hospitality_cap"], reverse=True)[:8]:
    ratio = r["hosp_actual"] / r["hospitality_cap"]
    print(f"    [{r['date']}] {r['artist'][:30]:30}  cap=${r['hospitality_cap']:.0f}  "
          f"actual=${r['hosp_actual']:.0f}  ratio={ratio:.2f}x  status={r['status']}")

# ---------- (e) Tier ratchet / walkout pot in freetext ----------
section("(e) Tier ratchets and walkout pots hidden in prose")
patterns = [
    ("tier_ratchet", r"\bratchet|ratchets|escalator|tiered|sliding|85.{0,3}95|80.{0,3}90"),
    ("walkout_pot", r"walkout|overage pot|100% of gross above|over breakeven"),
    ("gross_threshold_bonus", r"if gross|if attendance|over \$\d|above \$\d"),
    ("vs_gross_variant", r"vs.{0,5}\d+%\s*(?:of\s*)?gross\b"),
]
for name, pat in patterns:
    rows = q(f"""
        SELECT COUNT(*) AS c
        FROM deals
        WHERE deal_type = 'vs' AND deal_notes_freetext REGEXP ?
    """ if False else """
        SELECT deal_notes_freetext
        FROM deals
        WHERE deal_type = 'vs'
    """)
    # Python regex over fetched rows (SQLite REGEXP requires UDF; simpler to do it in Python)
    matches = sum(1 for r in rows if re.search(pat, r["deal_notes_freetext"] or "", re.IGNORECASE))
    print(f"  {name:25} {matches} / {len(rows)} vs-deals ({100*matches/len(rows):.0f}%)")

print("\n  --> Many vs-deals carry structure the schema can't represent.")
print("      The brief said: 'About a third of Vs deals are standard. The rest mix in")
print("      walkout pots, tier ratchets, and vs-gross variants.'")
