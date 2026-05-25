"""
Q13 — Stress-test signal (viii) before adopting it.

Signal (viii) as proposed: "deal doesn't mention marketing recoup, but
expenses table has marketing line items (Instagram boost / Spotify ad /
Local radio spot) for this show → flag as pre-flight risk for surprise
recoup at settlement."

Arshdeep's concern: we can't tell from the seed WHEN these expenses
were entered (only 3 distinct entered_at values in 2,943 rows). So the
Wednesday-knowability claim isn't testable. Let me at least test the
PATTERN: do disputed shows correlate with this signal regardless of
timing?

Questions to answer:
  (a) Of the 24 disputed shows, how many have marketing line items in
      expenses? How many of THOSE have a deal that mentions recoup?
      → if (marketing expense exists) ∧ (deal doesn't mention recoup)
        correlates strongly with dispute, the PATTERN works.
  (b) Same for paid/finalized (counter-population). What's the precision?
  (c) Does the same pattern work for hospitality ("Hospitality overage")?
  (d) Can we be specific about when marketing expense entries SHOULD be
      Wednesday-knowable in operational reality — vs. when they're inputs
      we honestly can't predict?

Then I can either:
  - Keep signal (viii) but caveat it as "production-only; backtest measures
    the pattern, not the timing"
  - Replace it with a different formulation
  - Drop it entirely
"""
import sqlite3, os, json, re
DB = os.path.join(os.path.dirname(__file__), "..", "..", "data", "greenroom.db")
conn = sqlite3.connect(DB)
conn.row_factory = sqlite3.Row

def q(sql, *params):
    return [dict(r) for r in conn.execute(sql, params).fetchall()]

def section(t):
    print("\n" + "=" * 78); print(t); print("=" * 78)

# Helper: deal-prose mentions any marketing-recoup language?
def deal_mentions_marketing_recoup(deal_notes):
    if not deal_notes: return False
    t = deal_notes.lower()
    return bool(re.search(r"marketing|recoup|ad spend|promo|spotify|boost|instagram|radio", t))

def deal_mentions_any_recoup(deal_notes):
    if not deal_notes: return False
    t = deal_notes.lower()
    return bool(re.search(r"recoup|overage|rider|prior advance|absorb", t))

# Marketing-typical expense descriptions
mkt_keywords = ["instagram boost", "spotify ad", "local radio spot", "ad spend"]
def show_has_marketing_expense(show_id):
    rows = q("""
        SELECT description, amount FROM expenses
        WHERE show_id = ? AND category = 'marketing'
    """, show_id)
    matched = [r for r in rows if r["description"] and
               any(k in r["description"].lower() for k in mkt_keywords)]
    total_mkt = sum(r["amount"] for r in matched)
    return (len(matched) > 0, total_mkt)

# Hospitality overage as a literal description
def show_has_hosp_overage_description(show_id):
    rows = q("""
        SELECT description, amount FROM expenses
        WHERE show_id = ? AND category = 'hospitality'
          AND description IS NOT NULL AND LOWER(description) LIKE '%overage%'
    """, show_id)
    return (len(rows) > 0, sum(r["amount"] for r in rows))

# -------------------------------------------------------------------------
section("(a) Disputed shows: marketing-expense + deal-silent-on-recoup pattern")
# -------------------------------------------------------------------------
disputed = q("""
    SELECT sh.id AS show_id, sh.date, a.name AS artist, d.deal_notes_freetext,
           s.recoups_json, s.status
    FROM settlements s
    JOIN shows sh ON sh.id = s.show_id
    JOIN artists a ON a.id = sh.artist_id
    JOIN deals d ON d.show_id = sh.id
    WHERE s.status = 'disputed'
""")
has_mkt_and_silent = 0
has_mkt = 0
print(f"  {'date':12} {'artist':22} mkt_exp? deal_recoup? signal_(viii)_fires?")
for d in disputed:
    has_mkt_exp, mkt_total = show_has_marketing_expense(d["show_id"])
    if has_mkt_exp: has_mkt += 1
    deal_mentions = deal_mentions_any_recoup(d["deal_notes_freetext"])
    fires = has_mkt_exp and not deal_mentions
    if fires: has_mkt_and_silent += 1
    print(f"  {d['date']}  {d['artist'][:21]:22}  {'yes' if has_mkt_exp else 'no ':3} (${mkt_total:>4.0f})  "
          f"{'yes' if deal_mentions else 'no ':3}            {'FIRE' if fires else '   '}")

print(f"\n  Disputed shows where signal (viii) fires: {has_mkt_and_silent}/{len(disputed)} = {100*has_mkt_and_silent/len(disputed):.0f}%")
print(f"  Disputed shows with any marketing expense at all:  {has_mkt}/{len(disputed)} = {100*has_mkt/len(disputed):.0f}%")

# -------------------------------------------------------------------------
section("(b) Same signal on paid/finalized — precision")
# -------------------------------------------------------------------------
paid = q("""
    SELECT sh.id AS show_id, d.deal_notes_freetext, s.status
    FROM settlements s
    JOIN shows sh ON sh.id = s.show_id
    JOIN deals d ON d.show_id = sh.id
    WHERE s.status IN ('paid', 'finalized')
""")
paid_fires = 0
paid_has_mkt = 0
for p in paid:
    has_mkt_exp, _ = show_has_marketing_expense(p["show_id"])
    if has_mkt_exp: paid_has_mkt += 1
    deal_mentions = deal_mentions_any_recoup(p["deal_notes_freetext"])
    if has_mkt_exp and not deal_mentions: paid_fires += 1
print(f"  Paid/finalized shows where signal (viii) fires: {paid_fires}/{len(paid)} = {100*paid_fires/len(paid):.0f}%")
print(f"  Paid/finalized with any marketing expense:        {paid_has_mkt}/{len(paid)} = {100*paid_has_mkt/len(paid):.0f}%")
print(f"\n  Confusion-matrix style:")
TP = has_mkt_and_silent
FN = len(disputed) - has_mkt_and_silent
FP = paid_fires
TN = len(paid) - paid_fires
print(f"    Treating 'signal (viii) fires' as alarm:")
print(f"    TP={TP}  FN={FN}  FP={FP}  TN={TN}")
print(f"    Recall    = {TP}/{TP+FN} = {100*TP/(TP+FN):.1f}%")
print(f"    Precision = {TP}/{TP+FP} = {100*TP/(TP+FP):.1f}%")
print(f"    Fire-rate on paid: {FP}/{len(paid)} = {100*FP/len(paid):.1f}%")

# -------------------------------------------------------------------------
section("(c) 'Hospitality overage' description as a literal signal")
# -------------------------------------------------------------------------
hosp_disp = 0
for d in disputed:
    has_ov, _ = show_has_hosp_overage_description(d["show_id"])
    if has_ov: hosp_disp += 1
hosp_paid = 0
for p in paid:
    has_ov, _ = show_has_hosp_overage_description(p["show_id"])
    if has_ov: hosp_paid += 1
print(f"  'Hospitality overage' description present:")
print(f"    On disputed:  {hosp_disp}/{len(disputed)} = {100*hosp_disp/len(disputed):.0f}%")
print(f"    On paid:      {hosp_paid}/{len(paid)} = {100*hosp_paid/len(paid):.0f}%")
print(f"\n  This is the ratio that matters: does presence of 'Hospitality overage'")
print(f"  description correlate with dispute? Lift = ratio_dispute / ratio_paid")
if hosp_paid > 0 and len(paid) > 0:
    lift = (hosp_disp/len(disputed)) / (hosp_paid/len(paid))
    print(f"  Lift = {lift:.2f}x (>1 means correlated with dispute)")

# -------------------------------------------------------------------------
section("(d) Wednesday-knowability — operational reality check")
# -------------------------------------------------------------------------
print("""
  Conceptual analysis (NOT in this seed; this is operational reasoning):

  Marketing expense entry timing in real venue operations:
    - Instagram boost: paid at campaign start, runs 2-3 weeks
    - Spotify ad: paid at campaign start, runs 2-3 weeks
    - Local radio spot: contracted 2-4 weeks ahead, paid before/after run
    → ALL of these are CONCEPTUALLY pre-show by 1-3 weeks

  Hospitality expense entry timing:
    - Pre-show purchases (booze, food order): 1-3 days before
    - Show-day consumption: night-of
    - 'Overage' realization: typically AFTER show
    → 'Hospitality overage' is operationally a POST-show description

  This seed doesn't model entry timing (3 distinct entered_at values).
  So we can't BACKTEST these as Wednesday-honest signals.

  BUT in production:
    - Signal (viii) marketing-expense + silent-deal: Wednesday-honest
      IF the venue enters ad spend as campaigns launch (which is when
      they're invoiced — operationally normal)
    - Signal "hospitality overage description": NOT Wednesday-honest.
      Always a post-show label.

  Honest framing for memo: Signal (viii) tests a PATTERN that does
  correlate with disputes (see (b) results above). Wednesday-honesty
  requires the venue to maintain current marketing-spend entry — a
  production data-currency requirement we surface as a system
  requirement, not as a built-in assumption.
""")
