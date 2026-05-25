"""
Q12 — Audit unstructured text fields I haven't queried.

Arshdeep noticed agents.preferences_notes has rich content. Audit ALL
remaining text fields for hidden value:

  (a) agents.preferences_notes        ← MISS, the headline
  (b) comps.notes                     ← not queried
  (c) expenses.description            ← not queried in detail
  (d) artists.manager_email           ← interesting? per-artist DM channel
  (e) shows.internal_notes            ← queried (D9), full pass for completeness
  (f) settlements.signoff_text concentration & oddities
  (g) Any other text column I might have skipped
"""
import sqlite3, os, re
from collections import Counter

DB = os.path.join(os.path.dirname(__file__), "..", "..", "data", "greenroom.db")
conn = sqlite3.connect(DB)
conn.row_factory = sqlite3.Row

def q(sql, *params):
    return [dict(r) for r in conn.execute(sql, params).fetchall()]

def section(t):
    print("\n" + "=" * 78); print(t); print("=" * 78)

# ---------------------------------------------------------------------------
section("(a) agents.preferences_notes — full content for all 14 agents")
# ---------------------------------------------------------------------------
rows = q("""
    SELECT a.id, a.name, ag.name AS agency, a.email, a.preferences_notes
    FROM agents a
    LEFT JOIN agencies ag ON ag.id = a.agency_id
    ORDER BY ag.name, a.name
""")
print(f"  Total agents: {len(rows)}")
filled = 0
for r in rows:
    if r["preferences_notes"]:
        filled += 1
print(f"  With non-null preferences_notes: {filled}/{len(rows)}\n")

for r in rows:
    print(f"  --- {r['name']} ({r['agency']}) — {r['email']}")
    if r["preferences_notes"]:
        for line in r["preferences_notes"].splitlines():
            print(f"      | {line}")
    else:
        print(f"      | <NULL>")

# ---------------------------------------------------------------------------
section("(b) comps.notes — content distribution")
# ---------------------------------------------------------------------------
rows = q("""
    SELECT category, notes, COUNT(*) AS c
    FROM comps
    WHERE notes IS NOT NULL AND notes != ''
    GROUP BY category, notes
    ORDER BY c DESC
""")
print(f"  Distinct (category, notes) tuples with non-null notes: {len(rows)}")
for r in rows[:20]:
    print(f"    {r['c']:3}× [{r['category']:14}] {r['notes'][:80]!r}")

n = q("SELECT COUNT(*) AS c FROM comps WHERE notes IS NOT NULL AND notes != ''")[0]['c']
total = q("SELECT COUNT(*) AS c FROM comps")[0]['c']
print(f"\n  Comp rows with non-null notes: {n}/{total} ({100*n/total:.0f}%)")

# ---------------------------------------------------------------------------
section("(c) expenses.description — content distribution")
# ---------------------------------------------------------------------------
n = q("SELECT COUNT(*) AS c FROM expenses WHERE description IS NOT NULL AND description != ''")[0]['c']
total = q("SELECT COUNT(*) AS c FROM expenses")[0]['c']
print(f"  Expense rows with non-null description: {n}/{total} ({100*n/total:.0f}%)")

# Top descriptions by category
for cat in ['hospitality','marketing','production','sound','lights','backline','security','other']:
    rows = q("""
        SELECT description, COUNT(*) AS c
        FROM expenses
        WHERE category = ? AND description IS NOT NULL AND description != ''
        GROUP BY description
        ORDER BY c DESC LIMIT 8
    """, cat)
    if rows:
        print(f"\n  Top {cat} descriptions:")
        for r in rows:
            print(f"    {r['c']:3}× {r['description'][:80]!r}")

# Look for descriptions that hint at recoup-relevant content
print("\n  Expense descriptions mentioning 'recoup' / 'pre-show' / 'ad' / 'promotion' / 'instagram' / 'spotify':")
rows = q("""
    SELECT category, description, amount, show_id
    FROM expenses
    WHERE description IS NOT NULL
      AND (LOWER(description) LIKE '%recoup%'
        OR LOWER(description) LIKE '%pre-show%'
        OR LOWER(description) LIKE '%instagram%'
        OR LOWER(description) LIKE '%spotify%'
        OR LOWER(description) LIKE '%boost%'
        OR LOWER(description) LIKE '%ad spend%'
        OR LOWER(description) LIKE '%promo%')
    LIMIT 20
""")
for r in rows:
    print(f"    [{r['category']:12}] ${r['amount']:.0f}  {r['description'][:120]}")

# ---------------------------------------------------------------------------
section("(d) artists table — what's in here besides what I used?")
# ---------------------------------------------------------------------------
rows = q("""
    SELECT a.name, a.genre, a.prior_show_count, a.manager_email,
           ag.name AS agent, agcy.name AS agency
    FROM artists a
    LEFT JOIN agents ag ON ag.id = a.agent_id
    LEFT JOIN agencies agcy ON agcy.id = ag.agency_id
    ORDER BY a.prior_show_count DESC
    LIMIT 20
""")
print(f"  Top 20 artists by prior_show_count:")
print(f"  {'name':25} {'genre':15} {'prior':>5}  {'agent':22} {'manager_email':30}")
for r in rows:
    me = r['manager_email'] or '<null>'
    print(f"  {r['name'][:24]:25} {(r['genre'] or '?')[:14]:15} {r['prior_show_count']:>5}  "
          f"{(r['agent'] or '<indep>')[:21]:22} {me[:29]:30}")

# manager_email population rate
n = q("SELECT COUNT(*) AS c FROM artists WHERE manager_email IS NOT NULL")[0]['c']
total = q("SELECT COUNT(*) AS c FROM artists")[0]['c']
print(f"\n  Artists with manager_email: {n}/{total} ({100*n/total:.0f}%)")

# Genre distribution
print("\n  Genre distribution:")
rows = q("SELECT genre, COUNT(*) AS c FROM artists GROUP BY genre ORDER BY c DESC")
for r in rows:
    print(f"    {(r['genre'] or '<null>'):20} {r['c']}")

# ---------------------------------------------------------------------------
section("(e) settlements.signoff_text — full distinct list (any oddities)")
# ---------------------------------------------------------------------------
rows = q("""
    SELECT signoff_text, COUNT(*) AS c
    FROM settlements
    WHERE signoff_text IS NOT NULL
    GROUP BY signoff_text
    ORDER BY c DESC
""")
print(f"  Distinct signoff_text values: {len(rows)}")
for r in rows:
    print(f"    {r['c']:>4}  {r['signoff_text']!r}")

# ---------------------------------------------------------------------------
section("(f) Cross-check: agents whose preferences_notes mention dispute language")
# ---------------------------------------------------------------------------
rows = q("""
    SELECT a.name, ag.name AS agency, a.preferences_notes,
           COUNT(s.id) AS settlement_count,
           SUM(CASE WHEN s.status='disputed' THEN 1 ELSE 0 END) AS disputes,
           SUM(CASE WHEN s.status IN ('disputed','revised','finalized') THEN 1 ELSE 0 END) AS dispute_episodes
    FROM agents a
    LEFT JOIN agencies ag ON ag.id = a.agency_id
    LEFT JOIN artists art ON art.agent_id = a.id
    LEFT JOIN shows sh ON sh.artist_id = art.id
    LEFT JOIN settlements s ON s.show_id = sh.id
    WHERE a.preferences_notes IS NOT NULL
    GROUP BY a.id
    ORDER BY dispute_episodes DESC
""")
print(f"  Agents with preferences_notes + dispute counts:\n")
for r in rows:
    print(f"  {r['name']:25} ({r['agency']:12})  shows={r['settlement_count']:3}  "
          f"disputed={r['disputes']:>2}  episodes={r['dispute_episodes']:>2}")
    if r["preferences_notes"]:
        for line in r["preferences_notes"].splitlines()[:5]:
            print(f"      | {line[:110]}")
    print()
