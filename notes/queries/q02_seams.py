"""
Q02 — Hunt for the planted seams the brief flagged.

The brief explicitly told us: "What the UI shows you isn't always what the
data says — and neither is necessarily what actually happened." It also
showed one example: settlements with `status='disputed'` but sign-off text
that reads positive.

We're looking for:
  (a) Disputed-status-with-positive-signoff (the planted example)
  (b) Coastal Spell — verify the dispute thread numbers match the DB
  (c) WME marketing-recoup pattern — Mariana said "third time this year"
  (d) Structured fields drifting from the freetext prose
  (e) Anything else that looks too clean and might be hiding something

Run from repo root:
    python notes/queries/q02_seams.py
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

# ---------- (a) Disputed-with-positive-signoff ----------
section("(a) Disputed status with positive sign-off text")

positive_phrases = [
    "looks good", "all good", "lgtm", "approved", "no issues",
    "signed off", "fine", "ok ", "ok.", "confirmed", "thanks", "no concerns",
    "no questions",
]
rows = q("""
    SELECT s.id, s.show_id, s.status, s.signoff_text, sh.date, a.name AS artist
    FROM settlements s
    JOIN shows sh ON sh.id = s.show_id
    JOIN artists a ON a.id = sh.artist_id
    WHERE s.status = 'disputed'
""")
print(f"Total disputed: {len(rows)}")
suspect = []
for r in rows:
    txt = (r["signoff_text"] or "").lower()
    if any(p in txt for p in positive_phrases):
        suspect.append(r)
print(f"Disputed-but-positive sign-off matches: {len(suspect)}")
for r in suspect[:15]:
    print(f"  {r['date']}  {r['artist'][:30]:30}  status={r['status']:10}  signoff={(r['signoff_text'] or '')[:90]!r}")

# ---------- Also: signed/finalized/paid with negative or dispute-y sign-off? ----------
section("(a.2) Signed/paid status with NEGATIVE sign-off — the inverse seam")
neg_phrases = ["dispute", "off ", "wrong", "discrepan", "doesn't match", "issue", "incorrect", "??", "concern"]
rows = q("""
    SELECT s.id, s.show_id, s.status, s.signoff_text, sh.date, a.name AS artist
    FROM settlements s
    JOIN shows sh ON sh.id = s.show_id
    JOIN artists a ON a.id = sh.artist_id
    WHERE s.status IN ('signed','finalized','paid')
      AND s.signoff_text IS NOT NULL
""")
neg = []
for r in rows:
    txt = (r["signoff_text"] or "").lower()
    if any(p in txt for p in neg_phrases):
        neg.append(r)
print(f"Signed/finalized/paid total: {len(rows)}")
print(f"With negative-ish sign-off: {len(neg)}")
for r in neg[:15]:
    print(f"  {r['date']}  {r['artist'][:30]:30}  status={r['status']:10}  signoff={(r['signoff_text'] or '')[:120]!r}")

# ---------- (b) Coastal Spell — does the dispute thread match the data? ----------
section("(b) Coastal Spell — March 14, 2025 — verify dispute-thread.md numbers")
rows = q("""
    SELECT sh.id AS show_id, sh.date, a.name AS artist, d.deal_type, d.guarantee_amount,
           d.percentage, d.percentage_basis, d.expense_cap, d.hospitality_cap,
           d.deal_notes_freetext,
           t.gross AS ticket_gross, t.fees AS ticket_fees, t.qty AS tickets_sold,
           s.status, s.gross_box_office, s.net_box_office, s.total_expenses, s.total_to_artist,
           s.recoups_json, s.signoff_text, s.notes
    FROM shows sh
    JOIN artists a ON a.id = sh.artist_id
    JOIN deals d ON d.show_id = sh.id
    LEFT JOIN ticket_sales t ON t.show_id = sh.id
    LEFT JOIN settlements s ON s.show_id = sh.id
    WHERE a.name LIKE '%Coastal Spell%'
    ORDER BY sh.date
""")
print(f"Coastal Spell shows in DB: {len(rows)}")
for r in rows:
    print(f"\n  show_id={r['show_id']}  date={r['date']}")
    for k, v in r.items():
        if v is None: continue
        if k == "deal_notes_freetext" and v:
            print(f"    {k}:")
            for line in v.splitlines():
                print(f"      | {line}")
        elif k == "recoups_json" and v:
            try:
                parsed = json.loads(v)
                print(f"    recoups_json (parsed): {json.dumps(parsed, indent=4)}")
            except Exception:
                print(f"    recoups_json (raw): {v}")
        else:
            print(f"    {k}: {v}")

# ---------- (c) WME marketing-recoup pattern ----------
section("(c) Marketing recoups across WME-agency deals")
rows = q("""
    SELECT sh.date, ar.name AS artist, ag.name AS agency, s.status, s.recoups_json,
           d.deal_type, d.deal_notes_freetext
    FROM settlements s
    JOIN shows sh ON sh.id = s.show_id
    JOIN deals d ON d.show_id = sh.id
    JOIN artists ar ON ar.id = sh.artist_id
    LEFT JOIN agents ag2 ON ag2.id = ar.agent_id
    LEFT JOIN agencies ag ON ag.id = ag2.agency_id
    WHERE ag.name LIKE '%WME%'
      AND s.recoups_json IS NOT NULL
      AND s.recoups_json != ''
      AND s.recoups_json != '[]'
    ORDER BY sh.date DESC
""")
print(f"WME settlements with any recoup line: {len(rows)}")
mkt_count = 0
mkt_disputed = 0
for r in rows:
    try:
        recoups = json.loads(r["recoups_json"])
    except Exception:
        continue
    has_mkt = any(x.get("category") == "marketing" for x in recoups)
    if has_mkt:
        mkt_count += 1
        mkt_disputed_here = any(
            x.get("category") == "marketing" and x.get("status") == "disputed"
            for x in recoups
        )
        if mkt_disputed_here:
            mkt_disputed += 1
        print(f"  {r['date']}  {r['artist'][:30]:30}  status={r['status']:10}  "
              f"deal={r['deal_type']:20}  "
              f"mkt_disputed={mkt_disputed_here}")
print(f"\n  WME settlements with a marketing recoup: {mkt_count}")
print(f"  WME settlements with a marketing recoup that was DISPUTED: {mkt_disputed}")

# ---------- (d) Structured-vs-freetext drift sampling ----------
section("(d) Drift: structured fields mismatch deal_notes_freetext (sample)")
# Heuristic: if the freetext mentions a number that doesn't appear in the
# structured fields, that's drift. Sample 20 vs-deals and eyeball.
sample = q("""
    SELECT sh.date, a.name AS artist, d.deal_type, d.guarantee_amount,
           d.percentage, d.percentage_basis, d.expense_cap, d.hospitality_cap,
           d.bonuses_json, d.deal_notes_freetext
    FROM deals d
    JOIN shows sh ON sh.id = d.show_id
    JOIN artists a ON a.id = sh.artist_id
    WHERE d.deal_type = 'vs'
    ORDER BY sh.date DESC
    LIMIT 20
""")
def numbers_in(s):
    return set(re.findall(r"\$?(\d[\d,]*)", s or ""))
drift_cases = 0
for r in sample:
    txt = r["deal_notes_freetext"] or ""
    nums_in_prose = numbers_in(txt)
    nums_in_struct = set()
    for k in ("guarantee_amount", "percentage", "expense_cap", "hospitality_cap"):
        v = r[k]
        if v is None: continue
        # store both the raw and the integer-rounded form (handle 0.8 -> 80 percent)
        nums_in_struct.add(str(v))
        try:
            iv = int(round(float(v)))
            nums_in_struct.add(str(iv))
            nums_in_struct.add(str(int(round(float(v) * 100))))  # percentages
        except Exception:
            pass
    prose_only = {n for n in nums_in_prose if n.replace(",", "") not in {x.replace(",", "") for x in nums_in_struct}}
    # Drop obviously trivial numbers
    prose_only = {n for n in prose_only if int(n.replace(",", "")) >= 50}
    if prose_only:
        drift_cases += 1
        print(f"\n  {r['date']}  {r['artist'][:30]:30}  vs-deal")
        print(f"    structured: guar={r['guarantee_amount']}  pct={r['percentage']}  "
              f"exp_cap={r['expense_cap']}  hosp_cap={r['hospitality_cap']}")
        print(f"    numbers in freetext NOT in structured: {sorted(prose_only)}")
        print(f"    freetext: {txt[:300]!r}")
print(f"\n  Drift detected in {drift_cases} of 20 sampled vs-deals.")
