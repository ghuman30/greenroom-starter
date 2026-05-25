"""
Q06 — Follow up on patterns Q05 surfaced.

(a) The "Comp tickets: 12. Revenue impact accepted." boilerplate — what's
    actually on those shows? Are comps anomalously high? Same comp count?
    Same artist? Same time period? Boilerplate suggests a planted seam.
(b) Briar Road full record — second hero case (TM signed, assistant disputed)
(c) Wet Cement full record — "paid but unresolved" case
(d) Coastal Spell's OTHER 2025-03-14 show (show_0152) — what's disputed?
(e) Tier ratchets: cross-check bonuses_json vs freetext
(f) Disputed-status state-machine path: do disputed shows go through signed?
(g) Settlement status x signoff_text crosstab — full picture
"""
import sqlite3, os, json, re
DB = os.path.join(os.path.dirname(__file__), "..", "..", "data", "greenroom.db")
conn = sqlite3.connect(DB)
conn.row_factory = sqlite3.Row

def q(sql, *params):
    return [dict(r) for r in conn.execute(sql, params).fetchall()]

def section(t):
    print("\n" + "=" * 78); print(t); print("=" * 78)

# (a) Boilerplate-comp shows
section("(a) The 'Comp tickets: 12. Revenue impact accepted.' shows — what's on them?")
rows = q("""
    SELECT sh.id, sh.date, a.name AS artist, s.status, s.gross_box_office,
           t.qty AS tickets_sold, d.deal_type
    FROM settlements s
    JOIN shows sh ON sh.id = s.show_id
    JOIN artists a ON a.id = sh.artist_id
    JOIN deals d ON d.show_id = sh.id
    LEFT JOIN ticket_sales t ON t.show_id = sh.id
    WHERE s.notes LIKE '%Comp tickets: 12%'
    ORDER BY sh.date
""")
print(f"Shows with that boilerplate: {len(rows)}")
for r in rows:
    # Get comp breakdown
    comps = q("""SELECT category, count, counts_toward_gross FROM comps WHERE show_id = ?""", r["id"])
    total_comps = sum(c["count"] for c in comps)
    print(f"\n  [{r['date']}] {r['artist']:25}  status={r['status']:8}  deal={r['deal_type']:20}  sold={r['tickets_sold']}  total_comps={total_comps}")
    for c in comps:
        print(f"      {c['category']:14} count={c['count']:3} counts_toward_gross={c['counts_toward_gross']}")

# (b) Briar Road
section("(b) Briar Road — full record (TM signed, assistant disputed)")
rows = q("""
    SELECT sh.id, sh.date, a.name AS artist, d.deal_type, d.guarantee_amount,
           d.percentage, d.percentage_basis, d.expense_cap, d.hospitality_cap,
           d.deal_notes_freetext,
           t.gross AS ticket_gross, t.qty AS tickets_sold,
           s.status, s.total_to_artist, s.recoups_json, s.signoff_text, s.notes
    FROM shows sh
    JOIN artists a ON a.id = sh.artist_id
    JOIN deals d ON d.show_id = sh.id
    LEFT JOIN ticket_sales t ON t.show_id = sh.id
    LEFT JOIN settlements s ON s.show_id = sh.id
    WHERE a.name = 'Briar Road' AND sh.date = '2024-10-16'
""")
for r in rows:
    for k, v in r.items():
        if v is None or v == "" or v == "[]": continue
        if k == "recoups_json":
            try:
                print(f"  {k}: {json.dumps(json.loads(v), indent=4)}")
            except Exception:
                print(f"  {k}: {v}")
        else:
            print(f"  {k}: {v}")

# (c) Wet Cement
section("(c) Wet Cement 2026-06-17 — 'paid but unresolved'")
rows = q("""
    SELECT sh.id, sh.date, a.name AS artist, d.deal_type, d.guarantee_amount,
           d.percentage, d.percentage_basis, d.expense_cap, d.hospitality_cap,
           d.deal_notes_freetext,
           t.gross, t.qty,
           s.status, s.total_to_artist, s.recoups_json, s.signoff_text, s.notes,
           s.paid_at, s.disputed_at
    FROM shows sh
    JOIN artists a ON a.id = sh.artist_id
    JOIN deals d ON d.show_id = sh.id
    LEFT JOIN ticket_sales t ON t.show_id = sh.id
    LEFT JOIN settlements s ON s.show_id = sh.id
    WHERE a.name = 'Wet Cement' AND sh.date = '2026-06-17'
""")
for r in rows:
    for k, v in r.items():
        if v is None or v == "" or v == "[]": continue
        if k == "recoups_json":
            try:
                print(f"  {k}: {json.dumps(json.loads(v), indent=4)}")
            except Exception:
                print(f"  {k}: {v}")
        else:
            print(f"  {k}: {v}")

# (d) Coastal Spell's OTHER 2025-03-14 show (show_0152)
section("(d) show_0152 — Coastal Spell 2025-03-14 'the other dispute'")
rows = q("""
    SELECT sh.id, sh.date, d.*, s.*
    FROM shows sh
    JOIN deals d ON d.show_id = sh.id
    LEFT JOIN settlements s ON s.show_id = sh.id
    WHERE sh.id = 'show_0152'
""")
for r in rows:
    for k, v in r.items():
        if v is None or v == "" or v == "[]": continue
        if k == "recoups_json":
            try:
                print(f"  {k}: {json.dumps(json.loads(v), indent=4)}")
            except Exception:
                print(f"  {k}: {v}")
        elif k in ("deal_notes_freetext", "notes", "signoff_text"):
            print(f"  {k}: {v}")
        else:
            print(f"  {k}: {v}")

# (e) Tier ratchets cross-check
section("(e) Tier ratchets: bonuses_json vs freetext")
rows = q("""
    SELECT sh.id, sh.date, a.name AS artist, d.deal_notes_freetext, d.bonuses_json
    FROM deals d
    JOIN shows sh ON sh.id = d.show_id
    JOIN artists a ON a.id = sh.artist_id
    WHERE d.deal_type = 'vs'
""")
both = 0; only_freetext = 0; only_json = 0; neither = 0
for r in rows:
    txt = r["deal_notes_freetext"] or ""
    has_text = bool(re.search(r"ratchet|escalat|tier|sliding", txt, re.IGNORECASE))
    has_json = False
    if r["bonuses_json"]:
        try:
            for b in json.loads(r["bonuses_json"]):
                if b.get("type") == "tier_ratchet":
                    has_json = True
                    break
        except Exception:
            pass
    if has_text and has_json: both += 1
    elif has_text: only_freetext += 1
    elif has_json: only_json += 1
    else: neither += 1
print(f"  Both: {both}")
print(f"  Only freetext: {only_freetext}")
print(f"  Only bonuses_json: {only_json}")
print(f"  Neither (other prose patterns): {neither}")

# (f) Disputed-state path
section("(f) Disputed shows: how many went through signed?")
rows = q("""
    SELECT id, submitted_at, review_started_at, signed_at, disputed_at
    FROM settlements
    WHERE status = 'disputed'
""")
went_through_signed = 0
direct_dispute = 0
no_review = 0
for r in rows:
    if r["signed_at"] is not None:
        went_through_signed += 1
    elif r["review_started_at"] is not None:
        direct_dispute += 1
    else:
        no_review += 1
print(f"  Disputed shows that went through 'signed': {went_through_signed}")
print(f"  Disputed shows that went review -> dispute (no signed): {direct_dispute}")
print(f"  Disputed shows with no review_started_at either: {no_review}")
print(f"  Total disputed: {len(rows)}")

# (g) Status x signoff_text crosstab — full
section("(g) status x signoff_text crosstab")
rows = q("""
    SELECT status, signoff_text, COUNT(*) AS c
    FROM settlements
    GROUP BY status, signoff_text
    ORDER BY status, c DESC
""")
prev = None
for r in rows:
    if r["status"] != prev:
        print(f"\n  --- status={r['status']} ---")
        prev = r["status"]
    print(f"    {r['c']:>3}  {(r['signoff_text'] or '<NULL>')!r}")

# (h) Disputed-show dispute-window check using submitted_at (since signed_at is often null)
section("(h) Recompute dispute lag from submitted_at -> disputed_at")
rows = q("""
    SELECT id, submitted_at, review_started_at, signed_at, disputed_at
    FROM settlements WHERE status='disputed' AND disputed_at IS NOT NULL AND submitted_at IS NOT NULL
""")
in_hour = 0; same_day = 0; next_morning = 0; later = 0
for r in rows:
    diff_h = (r["disputed_at"] - r["submitted_at"]) / 3600
    if diff_h < 1: in_hour += 1
    elif diff_h < 12: same_day += 1
    elif diff_h < 36: next_morning += 1
    else: later += 1
print(f"  From submitted_at to disputed_at:")
print(f"    < 1h:           {in_hour}")
print(f"    1–12h:          {same_day}")
print(f"    12–36h:         {next_morning}")
print(f"    > 36h:          {later}")
