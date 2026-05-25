"""
Q08 — App-vs-DB audit.

Arshdeep noticed: app shows 22 disputed, DB has 24. Source of the gap is in
lib/queries.ts — every aggregate filters `shows.date <= today` (today =
2026-05-22). Future-dated shows are excluded from EVERY app surface that
reads through getAllShows() or getReports().

This script enumerates the full gap. For each metric the UI surfaces, we
compute:
  - app_value   (what /reports and /shows show — filtered to past)
  - db_value    (the unfiltered truth)
  - delta       (what's hidden from the operator)
  - examples    (specific shows hidden — important for the memo)

Beyond the simple "past vs future" issue, we also check second-order drift:
  - Shows whose shows.status hasn't been updated (still 'booked' for shows
    that already happened) — what does the app think of those?
  - Shows displayed in /shows that don't have a settlement row
  - Shows in the future with in-flight settlements that the operator can't
    see (a real operational risk)
"""
import sqlite3, os, json
from datetime import date
DB = os.path.join(os.path.dirname(__file__), "..", "..", "data", "greenroom.db")
TODAY = "2026-05-22"   # matches the system date
conn = sqlite3.connect(DB)
conn.row_factory = sqlite3.Row

def q(sql, *params):
    return [dict(r) for r in conn.execute(sql, params).fetchall()]

def section(t):
    print("\n" + "=" * 78); print(t); print("=" * 78)

# ---------------------------------------------------------------------------
section(f"(a) Date split (today = {TODAY})")
# ---------------------------------------------------------------------------
row = q("""
    SELECT
      SUM(CASE WHEN date <= ? THEN 1 ELSE 0 END) AS past,
      SUM(CASE WHEN date >  ? THEN 1 ELSE 0 END) AS future,
      COUNT(*) AS total
    FROM shows
""", TODAY, TODAY)[0]
print(f"  Past (date <= today):   {row['past']}")
print(f"  Future (date >  today): {row['future']}")
print(f"  Total in DB:            {row['total']}")
print(f"  App displays:           {row['past']} (the rest are hidden)")

# ---------------------------------------------------------------------------
section("(b) Settlement-status counts — APP vs DB")
# ---------------------------------------------------------------------------
print(f"  {'status':14} {'app':>5} {'db':>5} {'delta':>6}")
print("  " + "-" * 36)
total_app = 0; total_db = 0
for stat in ['draft','submitted','in_review','signed','disputed','revised','finalized','paid','voided']:
    a = q("""
        SELECT COUNT(*) AS c FROM settlements s
        JOIN shows sh ON sh.id = s.show_id
        WHERE sh.date <= ? AND s.status = ?
    """, TODAY, stat)[0]['c']
    d = q("SELECT COUNT(*) AS c FROM settlements WHERE status = ?", stat)[0]['c']
    delta = d - a
    total_app += a; total_db += d
    marker = "  <-- HIDDEN" if delta else ""
    print(f"  {stat:14} {a:>5} {d:>5} {delta:>6}{marker}")
print("  " + "-" * 36)
print(f"  {'TOTAL':14} {total_app:>5} {total_db:>5} {total_db - total_app:>6}")

# ---------------------------------------------------------------------------
section("(c) The specific shows the app HIDES — by settlement status")
# ---------------------------------------------------------------------------
rows = q("""
    SELECT sh.date, a.name AS artist, d.deal_type, s.status, s.signoff_text,
           s.notes, s.recoups_json
    FROM settlements s
    JOIN shows sh ON sh.id = s.show_id
    JOIN artists a ON a.id = sh.artist_id
    JOIN deals d ON d.show_id = sh.id
    WHERE sh.date > ?
    ORDER BY sh.date
""", TODAY)
print(f"Total future-dated shows with settlement records hidden from app: {len(rows)}")
hidden_by_status = {}
for r in rows:
    hidden_by_status.setdefault(r['status'], []).append(r)
for stat, items in hidden_by_status.items():
    print(f"\n  Hidden {stat}: {len(items)}")
    for r in items[:5]:
        print(f"    [{r['date']}] {r['artist'][:25]:25}  deal={r['deal_type']:20}")
        if r['notes']:
            print(f"      notes: {(r['notes'] or '')[:140]}")

# ---------------------------------------------------------------------------
section("(d) Future-dated settlements that are NOT in 'draft' — operational risk")
# ---------------------------------------------------------------------------
# These are settlements for shows that haven't happened yet but are already
# submitted/in_review/signed/disputed/paid. That's a real seed quirk worth
# noticing — it means even the DB has impossible states (you can't dispute
# a settlement for a show that hasn't happened yet).
rows = q("""
    SELECT sh.date, a.name AS artist, s.status, s.signoff_text, s.notes
    FROM settlements s
    JOIN shows sh ON sh.id = s.show_id
    JOIN artists a ON a.id = sh.artist_id
    WHERE sh.date > ? AND s.status NOT IN ('draft')
    ORDER BY sh.date
""", TODAY)
print(f"  Future shows with NON-draft settlements: {len(rows)}")
for r in rows[:20]:
    print(f"    [{r['date']}] {r['artist'][:25]:25}  status={r['status']:12}  signoff={(r['signoff_text'] or '<NULL>')!r}")

# ---------------------------------------------------------------------------
section("(e) Top-level metric drift the UI shows vs. truth")
# ---------------------------------------------------------------------------

# Disputed rate (the headline metric on /reports)
a_total = q("SELECT COUNT(*) AS c FROM settlements s JOIN shows sh ON sh.id=s.show_id WHERE sh.date<=?", TODAY)[0]['c']
a_disp  = q("SELECT COUNT(*) AS c FROM settlements s JOIN shows sh ON sh.id=s.show_id WHERE sh.date<=? AND s.status='disputed'", TODAY)[0]['c']
d_total = q("SELECT COUNT(*) AS c FROM settlements")[0]['c']
d_disp  = q("SELECT COUNT(*) AS c FROM settlements WHERE status='disputed'")[0]['c']
print(f"  Disputed rate (app):  {a_disp}/{a_total} = {100*a_disp/a_total:.1f}%")
print(f"  Disputed rate (DB):   {d_disp}/{d_total} = {100*d_disp/d_total:.1f}%")

# % of deals supported by in-app tool
a_total = q("SELECT COUNT(*) AS c FROM deals d JOIN shows sh ON sh.id=d.show_id WHERE sh.date<=?", TODAY)[0]['c']
a_sup   = q("SELECT COUNT(*) AS c FROM deals d JOIN shows sh ON sh.id=d.show_id WHERE sh.date<=? AND d.deal_type IN ('flat','percentage_of_gross')", TODAY)[0]['c']
d_total = q("SELECT COUNT(*) AS c FROM deals")[0]['c']
d_sup   = q("SELECT COUNT(*) AS c FROM deals WHERE deal_type IN ('flat','percentage_of_gross')")[0]['c']
print(f"  Unsupported deal types (app):  {100*(1-a_sup/a_total):.0f}%  ({a_total - a_sup}/{a_total})")
print(f"  Unsupported deal types (DB):   {100*(1-d_sup/d_total):.0f}%  ({d_total - d_sup}/{d_total})")

# Total to artists
a_amt = q("SELECT COALESCE(SUM(total_to_artist),0) AS s FROM settlements s JOIN shows sh ON sh.id=s.show_id WHERE sh.date<=?", TODAY)[0]['s']
d_amt = q("SELECT COALESCE(SUM(total_to_artist),0) AS s FROM settlements")[0]['s']
print(f"  Total paid to artists (app):  ${a_amt:,.0f}")
print(f"  Total paid to artists (DB):   ${d_amt:,.0f}  (delta: ${d_amt - a_amt:,.0f})")

# Recoups
a_rec = q("""SELECT COUNT(*) AS c FROM settlements s JOIN shows sh ON sh.id=s.show_id
             WHERE sh.date<=? AND s.recoups_json IS NOT NULL AND s.recoups_json != '' AND s.recoups_json != '[]'""", TODAY)[0]['c']
d_rec = q("""SELECT COUNT(*) AS c FROM settlements
             WHERE recoups_json IS NOT NULL AND recoups_json != '' AND recoups_json != '[]'""")[0]['c']
print(f"  Settlements with recoups (app): {a_rec}")
print(f"  Settlements with recoups (DB):  {d_rec}")

# ---------------------------------------------------------------------------
section("(f) shows.status vs settlement.status — is shows.status maintained?")
# ---------------------------------------------------------------------------
# The shows.status enum is booked/advanced/day_of/settled/closed.
# For past shows, we'd expect mostly 'settled' or 'closed'. For future, mostly
# 'booked' or 'advanced'. Let's verify.
rows = q("""
    SELECT
      CASE WHEN sh.date <= ? THEN 'past' ELSE 'future' END AS bucket,
      sh.status,
      COUNT(*) AS c
    FROM shows sh
    GROUP BY bucket, sh.status
    ORDER BY bucket, c DESC
""", TODAY)
prev = None
for r in rows:
    if r['bucket'] != prev:
        print(f"\n  {r['bucket']}:")
        prev = r['bucket']
    print(f"    {r['status']:12} {r['c']}")

# How many PAST shows still have shows.status='booked' (i.e., stale)?
n = q("SELECT COUNT(*) AS c FROM shows WHERE date <= ? AND status='booked'", TODAY)[0]['c']
print(f"\n  Past shows still marked 'booked' (stale): {n}")
n = q("SELECT COUNT(*) AS c FROM shows WHERE date <= ? AND status='advanced'", TODAY)[0]['c']
print(f"  Past shows still marked 'advanced' (stale): {n}")

# ---------------------------------------------------------------------------
section("(g) Hidden disputed shows — the SPECIFIC list (memo material)")
# ---------------------------------------------------------------------------
rows = q("""
    SELECT sh.date, a.name AS artist, d.deal_type, s.status, s.signoff_text,
           s.notes, s.disputed_at, ag.name AS agency
    FROM settlements s
    JOIN shows sh ON sh.id = s.show_id
    JOIN artists a ON a.id = sh.artist_id
    JOIN deals d ON d.show_id = sh.id
    LEFT JOIN agents ag2 ON ag2.id = a.agent_id
    LEFT JOIN agencies ag ON ag.id = ag2.agency_id
    WHERE sh.date > ? AND s.status = 'disputed'
    ORDER BY sh.date
""", TODAY)
print(f"  Disputed shows HIDDEN from the app's 'disputed' count: {len(rows)}")
for r in rows:
    print(f"    [{r['date']}] {r['artist']}  ({r['agency']})  deal={r['deal_type']}")
    print(f"      signoff: {(r['signoff_text'] or '<NULL>')!r}")
    if r['notes']:
        print(f"      notes: {r['notes'][:200]}")
    if r['disputed_at']:
        print(f"      disputed_at: {r['disputed_at']}")

# ---------------------------------------------------------------------------
section("(h) The agents/artists with HIDDEN dispute activity — relationships at risk")
# ---------------------------------------------------------------------------
# If a future dispute is invisible, the operator doesn't know the relationship
# is heading toward a problem. List them by agent.
rows = q("""
    SELECT ag.name AS agency, ag2.name AS agent, a.name AS artist, sh.date, s.status
    FROM settlements s
    JOIN shows sh ON sh.id = s.show_id
    JOIN artists a ON a.id = sh.artist_id
    LEFT JOIN agents ag2 ON ag2.id = a.agent_id
    LEFT JOIN agencies ag ON ag.id = ag2.agency_id
    WHERE sh.date > ? AND s.status IN ('disputed', 'revised')
    ORDER BY ag.name, sh.date
""", TODAY)
print(f"  Future shows with disputed/revised settlements by agent:")
for r in rows:
    print(f"    {r['agency'] or '-':15} {(r['agent'] or '-')[:20]:20}  {r['artist'][:25]:25}  {r['date']}  {r['status']}")

# ---------------------------------------------------------------------------
section("(i) Today's view: what would the operator see TODAY at 2026-05-22?")
# ---------------------------------------------------------------------------
# The case test environment is dated 2026-05-22. What's the *current week*?
rows = q("""
    SELECT sh.date, a.name AS artist, d.deal_type, s.status, s.signoff_text
    FROM shows sh
    JOIN artists a ON a.id = sh.artist_id
    JOIN deals d ON d.show_id = sh.id
    LEFT JOIN settlements s ON s.show_id = sh.id
    WHERE sh.date BETWEEN ? AND date(?, '+7 days')
    ORDER BY sh.date
""", TODAY, TODAY)
print(f"  Upcoming next 7 days: {len(rows)} shows")
for r in rows:
    print(f"    [{r['date']}] {r['artist'][:25]:25}  deal={r['deal_type']:20}  sett.status={r['status']}")
