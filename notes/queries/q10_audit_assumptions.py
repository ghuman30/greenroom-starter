"""
Q10 — Audit my design assumptions, especially around what data is
actually available on Wednesday.

Arshdeep flagged: my signal (iii) hospitality_overrun sums ALL expenses
for a show, but most hospitality is incurred on show day. If most hosp
spend isn't known Wednesday, my backtest is overstating recall — the
production system would have less data to work with than the backtest.

Other assumptions to audit:
  (a) When is `expenses.entered_at` actually populated? (Earlier I found
      ~2,500 expenses share the same seed timestamp; verify.)
  (b) For each expense category, what fraction of shows have expenses
      entered BEFORE show date vs ON/AFTER show date? (Tests whether
      categories like marketing are reliably pre-show.)
  (c) What does `ticket_sales.captured_at` look like — is it incremental
      or single-row-per-show?
  (d) Are there other timestamp fields I'm relying on that might be
      seed-artifacts?
"""
import sqlite3, os
from datetime import datetime, timezone

DB = os.path.join(os.path.dirname(__file__), "..", "..", "data", "greenroom.db")
conn = sqlite3.connect(DB)
conn.row_factory = sqlite3.Row

def q(sql, *params):
    return [dict(r) for r in conn.execute(sql, params).fetchall()]

def section(t):
    print("\n" + "=" * 78); print(t); print("=" * 78)

# ---------------------------------------------------------------------------
section("(a) expenses.entered_at distribution — is it real or seed artifact?")
# ---------------------------------------------------------------------------
rows = q("""
    SELECT entered_at, COUNT(*) AS c
    FROM expenses
    GROUP BY entered_at
    ORDER BY c DESC
    LIMIT 10
""")
print(f"  Top 10 entered_at timestamps and how many expenses share them:")
for r in rows:
    dt = datetime.fromtimestamp(r["entered_at"], tz=timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    print(f"    {r['entered_at']}  ({dt})  → {r['c']} expenses")

distinct = q("SELECT COUNT(DISTINCT entered_at) AS d, COUNT(*) AS c FROM expenses")[0]
print(f"\n  Distinct entered_at values: {distinct['d']} out of {distinct['c']} expense rows")
print(f"  Concentration ratio: {distinct['c']/distinct['d']:.1f} rows per distinct timestamp")

# ---------------------------------------------------------------------------
section("(b) Expense entered_at vs show date — is it pre-show or post-show?")
# ---------------------------------------------------------------------------
rows = q("""
    SELECT e.category,
           COUNT(*) AS total,
           SUM(CASE WHEN datetime(e.entered_at, 'unixepoch') < sh.date THEN 1 ELSE 0 END) AS pre_show,
           SUM(CASE WHEN datetime(e.entered_at, 'unixepoch') >= sh.date THEN 1 ELSE 0 END) AS on_or_post,
           SUM(CASE WHEN datetime(e.entered_at, 'unixepoch') < datetime(sh.date, '-3 days') THEN 1 ELSE 0 END) AS three_days_before
    FROM expenses e
    JOIN shows sh ON sh.id = e.show_id
    GROUP BY e.category
    ORDER BY total DESC
""")
print(f"  {'category':14} {'total':>6} {'pre_show':>9} {'on_or_post':>11} {'Wed-knowable':>13}")
print("  " + "-" * 60)
for r in rows:
    pct_pre = 100*r["pre_show"]/r["total"] if r["total"] else 0
    pct_wed = 100*r["three_days_before"]/r["total"] if r["total"] else 0
    print(f"  {r['category']:14} {r['total']:>6} {r['pre_show']:>9} ({pct_pre:>3.0f}%) {r['on_or_post']:>5} ({100-pct_pre:>3.0f}%)  {r['three_days_before']} ({pct_wed:>3.0f}%)")

# ---------------------------------------------------------------------------
section("(c) ticket_sales: incremental or single-row?")
# ---------------------------------------------------------------------------
n = q("""
    SELECT show_id, COUNT(*) AS rows_per_show
    FROM ticket_sales
    GROUP BY show_id
    ORDER BY rows_per_show DESC
    LIMIT 5
""")
print(f"  Top shows by ticket_sales row count:")
for r in n:
    print(f"    {r['show_id']}  rows={r['rows_per_show']}")
n = q("SELECT COUNT(DISTINCT show_id) AS shows, COUNT(*) AS rows_ FROM ticket_sales")[0]
print(f"  Total ticket_sales rows: {n['rows_']}, distinct shows: {n['shows']}")
print(f"  Average rows per show: {n['rows_']/n['shows']:.2f}")

n = q("""
    SELECT t.captured_at, sh.date, t.show_id
    FROM ticket_sales t JOIN shows sh ON sh.id = t.show_id
    ORDER BY t.captured_at LIMIT 5
""")
print(f"\n  Sample of ticket_sales.captured_at vs show date:")
for r in n:
    dt = datetime.fromtimestamp(r["captured_at"], tz=timezone.utc).strftime("%Y-%m-%d")
    print(f"    captured_at={dt}  show_date={r['date']}  show_id={r['show_id']}")

# ---------------------------------------------------------------------------
section("(d) Settlement timestamps — are they all seed?")
# ---------------------------------------------------------------------------
# Check submitted_at vs disputed_at etc. relative to show date
rows = q("""
    SELECT
      SUM(CASE WHEN drafted_at IS NOT NULL THEN 1 ELSE 0 END) AS w_drafted,
      SUM(CASE WHEN submitted_at IS NOT NULL THEN 1 ELSE 0 END) AS w_submitted,
      SUM(CASE WHEN disputed_at IS NOT NULL THEN 1 ELSE 0 END) AS w_disputed,
      SUM(CASE WHEN paid_at IS NOT NULL THEN 1 ELSE 0 END) AS w_paid,
      COUNT(*) AS total
    FROM settlements
""")[0]
print(f"  Population rates:")
for k in ["w_drafted", "w_submitted", "w_disputed", "w_paid"]:
    print(f"    {k:14}: {rows[k]}/{rows['total']}")

# Check: how often is drafted_at AFTER show date? Should be 0 (you draft after show)
n = q("""
    SELECT COUNT(*) AS c
    FROM settlements s
    JOIN shows sh ON sh.id = s.show_id
    WHERE s.drafted_at IS NOT NULL
      AND datetime(s.drafted_at, 'unixepoch') < datetime(sh.date)
""")[0]
print(f"\n  Settlements drafted BEFORE show date (impossible operationally): {n['c']}")

# Distinct timestamp count for drafted_at
n = q("SELECT COUNT(DISTINCT drafted_at) AS d FROM settlements WHERE drafted_at IS NOT NULL")[0]
print(f"  Distinct drafted_at timestamps: {n['d']}")

# ---------------------------------------------------------------------------
section("(e) Same audit on deals.created_at")
# ---------------------------------------------------------------------------
n = q("SELECT COUNT(DISTINCT created_at) AS d, COUNT(*) AS c FROM deals")[0]
print(f"  Distinct created_at timestamps in deals: {n['d']}/{n['c']}")
n = q("""
    SELECT COUNT(*) AS c FROM deals d
    JOIN shows sh ON sh.id = d.show_id
    WHERE datetime(d.created_at, 'unixepoch') > datetime(sh.date)
""")[0]
print(f"  Deals created AFTER their show date (impossible if deal is pre-show): {n['c']}")

# ---------------------------------------------------------------------------
section("(f) What CAN we trust as Wednesday-knowable in this dataset?")
# ---------------------------------------------------------------------------
print("  Based on the above, what timestamps are reliable for time-aware queries:")
print()
print("  RELIABLE:")
print("    - shows.date (the show's calendar date — set at booking)")
print()
print("  PROBABLY-RELIABLE (seed timestamps, but logically pre-show):")
print("    - deals.created_at (deal entry time — IF distinct values exist)")
print("    - settlements.submitted_at/disputed_at/paid_at (relative ordering")
print("      proven by Q04: most disputes open 12-36h after submission)")
print()
print("  NOT RELIABLE for 'when was this known':")
print("    - expenses.entered_at (if ~all expenses share one seed timestamp,")
print("      we cannot tell what was knowable on Wednesday from the DB)")
print()
print("  IMPLICATION FOR OUR DESIGN:")
print("  The honest move is to assume the venue/booker maintains an expense")
print("  pipeline that reflects what's known at any given moment, and design")
print("  for THAT operational model — not for what the seed data happens to")
print("  encode. Our pre-flight signals that touch expenses must be designed")
print("  around realistic operational knowability, not the seed's timestamps.")
