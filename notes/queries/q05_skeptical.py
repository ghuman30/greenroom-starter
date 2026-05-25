"""
Q05 — Adversarial skepticism pass.

For each thing the system *displays*, ask: could the data underneath be
saying something different? Run cross-table reconciliations, time-order
checks, and look for hidden stories in free-text fields.

Sections:
  (a) Math reconciliation: settlement.gross_box_office vs SUM(ticket_sales.gross)
  (b) Math reconciliation: settlement.total_expenses vs expenses table
  (c) Math reconciliation: settlement.total_to_artist — does it match dealMath?
  (d) Status-machine validity: timestamp ordering
  (e) Status-machine validity: status vs paid_at/signed_at presence
  (f) Show.status vs settlement.status reconciliation
  (g) Same-date-same-artist anomalies (we saw 2 Coastal Spells on 2025-03-14)
  (h) Settlement.notes — hidden stories
  (i) Show.internal_notes — hidden stories
  (j) Bonuses: % null, structure, "applied" status
  (k) percentage_basis distribution for vs deals (vs-gross vs vs-net mix)
  (l) Expense timestamps after settlement signed/paid
  (m) absorbed_by_venue patterns
  (n) calculation_json coverage
  (o) Comp distribution — counts_toward_gross weirdness
  (p) Negative or zero amounts; impossibly large amounts

Run:
    python -X utf8 notes/queries/q05_skeptical.py
"""
import sqlite3, os, json, re, statistics
from collections import Counter, defaultdict

DB = os.path.join(os.path.dirname(__file__), "..", "..", "data", "greenroom.db")
conn = sqlite3.connect(DB)
conn.row_factory = sqlite3.Row

def q(sql, *params):
    return [dict(r) for r in conn.execute(sql, params).fetchall()]

def section(title):
    print("\n" + "=" * 78)
    print(title)
    print("=" * 78)

# =============================================================================
section("(a) Math reconciliation: settlement.gross_box_office vs SUM(ticket_sales.gross)")
# =============================================================================
rows = q("""
    SELECT s.show_id, s.gross_box_office AS s_gross,
           COALESCE(SUM(t.gross), 0) AS ticket_gross,
           sh.date, a.name AS artist, s.status
    FROM settlements s
    JOIN shows sh ON sh.id = s.show_id
    JOIN artists a ON a.id = sh.artist_id
    LEFT JOIN ticket_sales t ON t.show_id = s.show_id
    WHERE s.gross_box_office IS NOT NULL
    GROUP BY s.show_id
""")
mismatches = [r for r in rows if abs((r["s_gross"] or 0) - (r["ticket_gross"] or 0)) > 0.5]
print(f"Settlements with gross_box_office set: {len(rows)}")
print(f"Settlements where settlement.gross != SUM(ticket_sales.gross): {len(mismatches)}")
for r in mismatches[:12]:
    diff = (r["s_gross"] or 0) - (r["ticket_gross"] or 0)
    print(f"  {r['date']}  {r['artist'][:25]:25}  s_gross=${r['s_gross']:.0f}  ticket_gross=${r['ticket_gross']:.0f}  diff=${diff:.0f}  status={r['status']}")

# =============================================================================
section("(b) Math reconciliation: settlement.total_expenses vs expenses table")
# =============================================================================
rows = q("""
    SELECT s.show_id, s.total_expenses AS s_exp,
           COALESCE(SUM(CASE WHEN e.absorbed_by_venue=0 THEN e.amount ELSE 0 END), 0) AS exp_passthrough,
           COALESCE(SUM(e.amount), 0) AS exp_all,
           sh.date, a.name AS artist, s.status
    FROM settlements s
    JOIN shows sh ON sh.id = s.show_id
    JOIN artists a ON a.id = sh.artist_id
    LEFT JOIN expenses e ON e.show_id = s.show_id
    WHERE s.total_expenses IS NOT NULL
    GROUP BY s.show_id
""")
m_passthrough = [r for r in rows if abs((r["s_exp"] or 0) - (r["exp_passthrough"] or 0)) > 0.5]
m_total = [r for r in rows if abs((r["s_exp"] or 0) - (r["exp_all"] or 0)) > 0.5]
print(f"Settlements with total_expenses set: {len(rows)}")
print(f"  vs SUM(expenses where !absorbed): {len(m_passthrough)} mismatches")
print(f"  vs SUM(expenses including absorbed): {len(m_total)} mismatches")
print("  Examples (vs passthrough):")
for r in m_passthrough[:8]:
    print(f"    {r['date']}  {r['artist'][:25]:25}  s_exp=${r['s_exp']:.0f}  passthrough=${r['exp_passthrough']:.0f}  all=${r['exp_all']:.0f}")

# =============================================================================
section("(d) Status-machine validity: timestamp ordering")
# =============================================================================
# Expected order: drafted < submitted < review_started < signed < (disputed?) < revised? < finalized? < paid
rows = q("""
    SELECT id, show_id, status, drafted_at, submitted_at, review_started_at,
           signed_at, disputed_at, revised_at, finalized_at, paid_at
    FROM settlements
""")
def order_check(r):
    seq = [
        ("drafted_at", r["drafted_at"]),
        ("submitted_at", r["submitted_at"]),
        ("review_started_at", r["review_started_at"]),
        ("signed_at", r["signed_at"]),
        ("disputed_at", r["disputed_at"]),
        ("revised_at", r["revised_at"]),
        ("finalized_at", r["finalized_at"]),
        ("paid_at", r["paid_at"]),
    ]
    seq = [(k, v) for k, v in seq if v is not None]
    issues = []
    for i in range(len(seq) - 1):
        if seq[i][1] > seq[i+1][1]:
            issues.append(f"{seq[i][0]} > {seq[i+1][0]}")
    return issues
violations = 0
sample = []
for r in rows:
    issues = order_check(r)
    if issues:
        violations += 1
        if len(sample) < 10:
            sample.append((r["id"], r["status"], issues))
print(f"Settlements with out-of-order timestamps: {violations}/{len(rows)}")
for s in sample:
    print(f"  {s[0]}  status={s[1]}  issues={s[2]}")

# =============================================================================
section("(e) Status-machine validity: status vs timestamp presence")
# =============================================================================
expected_ts = {
    "draft":     ["drafted_at"],
    "submitted": ["drafted_at", "submitted_at"],
    "in_review": ["drafted_at", "submitted_at", "review_started_at"],
    "signed":    ["drafted_at", "submitted_at", "review_started_at", "signed_at"],
    "disputed":  ["drafted_at", "submitted_at", "review_started_at", "disputed_at"],
    "revised":   ["drafted_at", "submitted_at", "review_started_at", "disputed_at", "revised_at"],
    "finalized": ["drafted_at", "submitted_at", "review_started_at", "finalized_at"],
    "paid":      ["drafted_at", "submitted_at", "review_started_at", "paid_at"],
    "voided":    [],
}
inconsistencies = defaultdict(int)
for r in rows:
    stat = r["status"]
    needed = expected_ts.get(stat, [])
    for k in needed:
        if r[k] is None:
            inconsistencies[(stat, f"missing {k}")] += 1
print("Status vs missing-required-timestamp counts:")
for k, c in sorted(inconsistencies.items(), key=lambda x: -x[1]):
    print(f"  {k[0]:10}  {k[1]:30}  {c}")

# Status implies signed_at should be set?
print("\nDisputed shows missing signed_at:")
rows2 = q("""SELECT COUNT(*) AS c FROM settlements WHERE status='disputed' AND signed_at IS NULL""")
print(f"  {rows2[0]['c']}/24 disputed shows have no signed_at")
rows2 = q("""SELECT COUNT(*) AS c FROM settlements WHERE status='paid' AND signed_at IS NULL""")
print(f"  {rows2[0]['c']}/447 paid shows have no signed_at")

# =============================================================================
section("(f) Show.status vs settlement.status reconciliation")
# =============================================================================
rows = q("""
    SELECT sh.status AS show_status, s.status AS sett_status, COUNT(*) AS c
    FROM shows sh
    LEFT JOIN settlements s ON s.show_id = sh.id
    GROUP BY sh.status, s.status
    ORDER BY c DESC
""")
print(f"{'show.status':15} {'settlement.status':18} count")
for r in rows:
    print(f"  {(r['show_status'] or '-'):15} {(r['sett_status'] or '-'):18} {r['c']}")

# =============================================================================
section("(g) Same-date-same-artist anomalies")
# =============================================================================
rows = q("""
    SELECT a.name AS artist, sh.date, COUNT(*) AS c, GROUP_CONCAT(sh.id, '|') AS show_ids
    FROM shows sh
    JOIN artists a ON a.id = sh.artist_id
    GROUP BY a.name, sh.date
    HAVING c > 1
    ORDER BY c DESC, sh.date DESC
""")
print(f"Same-date-same-artist clusters: {len(rows)}")
for r in rows[:20]:
    print(f"  {r['date']}  {r['artist']:30}  count={r['c']}  ids={r['show_ids']}")

# =============================================================================
section("(h) Settlement.notes — pull a sample of non-empty ones")
# =============================================================================
rows = q("""
    SELECT s.show_id, sh.date, a.name AS artist, s.status, s.notes
    FROM settlements s
    JOIN shows sh ON sh.id = s.show_id
    JOIN artists a ON a.id = sh.artist_id
    WHERE s.notes IS NOT NULL AND LENGTH(s.notes) > 30
    ORDER BY LENGTH(s.notes) DESC
""")
print(f"Settlements with substantive notes (>30 chars): {len(rows)}")
for r in rows[:12]:
    print(f"\n  [{r['date']}] {r['artist']}  status={r['status']}")
    print(f"  notes: {r['notes'][:400]}")

# =============================================================================
section("(i) Show.internal_notes — hidden stories")
# =============================================================================
rows = q("""
    SELECT sh.id, sh.date, a.name AS artist, sh.internal_notes
    FROM shows sh
    JOIN artists a ON a.id = sh.artist_id
    WHERE sh.internal_notes IS NOT NULL AND LENGTH(sh.internal_notes) > 30
    ORDER BY LENGTH(sh.internal_notes) DESC
""")
print(f"Shows with substantive internal_notes: {len(rows)}")
for r in rows[:12]:
    print(f"\n  [{r['date']}] {r['artist']}")
    print(f"  notes: {r['internal_notes'][:400]}")

# =============================================================================
section("(j) Bonuses_json — when present, do they actually trigger? Structure?")
# =============================================================================
rows = q("""
    SELECT d.show_id, d.bonuses_json, t.gross, t.qty, sh.date, a.name AS artist
    FROM deals d
    JOIN shows sh ON sh.id = d.show_id
    JOIN artists a ON a.id = sh.artist_id
    LEFT JOIN ticket_sales t ON t.show_id = d.show_id
    WHERE d.bonuses_json IS NOT NULL AND d.bonuses_json != '' AND d.bonuses_json != '[]'
""")
print(f"Deals with non-empty bonuses_json: {len(rows)}")
bonus_types = Counter()
triggered = 0
not_triggered = 0
sellout_with_no_cap = 0
for r in rows:
    try:
        bonuses = json.loads(r["bonuses_json"])
    except Exception:
        continue
    for b in bonuses:
        bonus_types[b.get("type", "?")] += 1
        if b.get("type") == "gross_threshold":
            if r["gross"] and r["gross"] >= b.get("threshold", 0):
                triggered += 1
            else:
                not_triggered += 1
        if b.get("type") == "sellout":
            # need capacity to evaluate; we know venue is 650
            if r["qty"] and r["qty"] >= 650 * 0.95:
                triggered += 1
            else:
                not_triggered += 1
print(f"Bonus type counts: {dict(bonus_types)}")
print(f"Gross-threshold + sellout bonuses that would trigger: {triggered}")
print(f"Same that would NOT trigger: {not_triggered}")

# =============================================================================
section("(k) percentage_basis for vs deals — vs-gross vs vs-net mix")
# =============================================================================
rows = q("""
    SELECT percentage_basis, COUNT(*) AS c
    FROM deals
    WHERE deal_type = 'vs'
    GROUP BY percentage_basis
""")
for r in rows:
    print(f"  {(r['percentage_basis'] or '<null>'):10}  {r['c']}")
# Plus: vs deals where percentage_basis is null
print()
print("vs deals where percentage_basis is NULL (the in-app tool wouldn't know how to settle):")
n = q("""SELECT COUNT(*) AS c FROM deals WHERE deal_type='vs' AND percentage_basis IS NULL""")
print(f"  {n[0]['c']}")

# =============================================================================
section("(l) Expense timestamps after settlement signed/paid")
# =============================================================================
rows = q("""
    SELECT sh.date, a.name AS artist, e.category, e.amount, e.entered_at,
           s.signed_at, s.paid_at, s.status
    FROM expenses e
    JOIN shows sh ON sh.id = e.show_id
    JOIN artists a ON a.id = sh.artist_id
    JOIN settlements s ON s.show_id = sh.id
    WHERE (s.signed_at IS NOT NULL AND e.entered_at > s.signed_at)
       OR (s.paid_at IS NOT NULL AND e.entered_at > s.paid_at)
""")
print(f"Expenses entered AFTER settlement signed or paid: {len(rows)}")
for r in rows[:12]:
    print(f"  {r['date']}  {r['artist'][:25]:25}  {r['category']:12}  ${r['amount']:.0f}  "
          f"entered={r['entered_at']}  signed={r['signed_at']}  paid={r['paid_at']}  status={r['status']}")

# =============================================================================
section("(m) absorbed_by_venue patterns — hidden venue subsidies")
# =============================================================================
rows = q("""
    SELECT category,
           COUNT(*) AS total,
           SUM(CASE WHEN absorbed_by_venue=1 THEN 1 ELSE 0 END) AS absorbed,
           SUM(CASE WHEN absorbed_by_venue=1 THEN amount ELSE 0 END) AS absorbed_amt,
           SUM(amount) AS total_amt
    FROM expenses
    GROUP BY category
    ORDER BY absorbed_amt DESC
""")
print(f"{'category':15} {'total':>6} {'absorbed':>10} {'$_absorbed':>12} {'$_total':>12} {'% absorbed':>10}")
for r in rows:
    rate = 100*r["absorbed"]/r["total"] if r["total"] else 0
    print(f"  {r['category']:14} {r['total']:>6} {r['absorbed']:>10} ${r['absorbed_amt']:>10.0f} ${r['total_amt']:>10.0f}   {rate:>5.1f}%")

# =============================================================================
section("(n) calculation_json coverage")
# =============================================================================
n = q("""
    SELECT
      SUM(CASE WHEN calculation_json IS NULL OR calculation_json='' THEN 1 ELSE 0 END) AS null_calc,
      COUNT(*) AS total
    FROM settlements
""")[0]
print(f"Settlements with null/empty calculation_json: {n['null_calc']}/{n['total']}")
n = q("""
    SELECT status, COUNT(*) AS c,
           SUM(CASE WHEN calculation_json IS NULL OR calculation_json='' THEN 1 ELSE 0 END) AS null_c
    FROM settlements
    GROUP BY status
""")
for r in n:
    print(f"  {r['status']:12} {r['c']:>4} total  {r['null_c']:>4} null_calc")

# =============================================================================
section("(o) Comp distribution + counts_toward_gross weirdness")
# =============================================================================
rows = q("""
    SELECT category,
           COUNT(*) AS rows_,
           SUM(count) AS tickets,
           SUM(CASE WHEN counts_toward_gross=1 THEN 1 ELSE 0 END) AS counts_in,
           SUM(CASE WHEN counts_toward_gross=1 THEN count ELSE 0 END) AS tickets_in
    FROM comps
    GROUP BY category
    ORDER BY tickets DESC
""")
print(f"{'category':14} {'rows':>5} {'tickets':>8} {'counts_in':>10} {'tickets_in':>11}")
for r in rows:
    print(f"  {r['category']:13} {r['rows_']:>5} {r['tickets']:>8} {r['counts_in']:>10} {r['tickets_in']:>11}")

# Mariana said comp policy "varies by deal." So same category should sometimes count, sometimes not.
print("\n  Categories that mix counts_toward_gross (sometimes yes, sometimes no):")
rows = q("""
    SELECT category,
           SUM(counts_toward_gross) AS yes,
           COUNT(*) - SUM(counts_toward_gross) AS no
    FROM comps
    GROUP BY category
    HAVING yes > 0 AND no > 0
""")
for r in rows:
    print(f"    {r['category']:14} yes={r['yes']:>4} no={r['no']:>4}")

# =============================================================================
section("(p) Negative or extreme amounts")
# =============================================================================
print("expenses with negative or zero amount:")
rows = q("SELECT category, amount, description, show_id FROM expenses WHERE amount <= 0")
print(f"  {len(rows)}")
for r in rows[:8]:
    print(f"  {r}")
print("\nticket_sales with negative or zero gross:")
rows = q("SELECT show_id, gross, fees, qty FROM ticket_sales WHERE gross <= 0")
print(f"  {len(rows)}")

print("\nticket_sales where fees > gross (shouldn't happen):")
rows = q("SELECT show_id, gross, fees, qty FROM ticket_sales WHERE fees > gross")
print(f"  {len(rows)}")
for r in rows[:8]:
    print(f"  {r}")

print("\nticket_sales with extreme fee ratios (>15% — typical ticketing is 8-12%):")
rows = q("SELECT show_id, gross, fees, qty FROM ticket_sales WHERE gross > 0 AND fees > gross*0.15")
print(f"  {len(rows)}")
