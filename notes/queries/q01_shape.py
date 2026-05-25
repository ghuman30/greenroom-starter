"""
Q01 — Shape checks. Before targeted hypotheses, look at the corpus.
What tables exist? What's the row count? What's the deal-type / settlement-
status distribution? Where are the NULLs concentrated?

Output is printed in markdown-tableish form to make it pasteable into
evidence.md.

Run from repo root:
    python notes/queries/q01_shape.py
"""
import sqlite3
import os
import json

DB = os.path.join(os.path.dirname(__file__), "..", "..", "data", "greenroom.db")

conn = sqlite3.connect(DB)
conn.row_factory = sqlite3.Row

def q(sql, *params):
    return [dict(r) for r in conn.execute(sql, params).fetchall()]

print("=" * 60)
print("Q01 — Corpus shape")
print("=" * 60)

print("\n--- Table row counts ---")
tables = q("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name")
for t in tables:
    name = t["name"]
    c = conn.execute(f"SELECT COUNT(*) AS c FROM {name}").fetchone()[0]
    print(f"  {name:20} {c}")

print("\n--- Deal type distribution (all shows) ---")
for r in q("SELECT deal_type, COUNT(*) AS c FROM deals GROUP BY deal_type ORDER BY c DESC"):
    print(f"  {r['deal_type']:25} {r['c']}")

print("\n--- Settlement status distribution ---")
for r in q("SELECT status, COUNT(*) AS c FROM settlements GROUP BY status ORDER BY c DESC"):
    print(f"  {r['status']:15} {r['c']}")

print("\n--- Deal type x settlement status ---")
print("  (only past shows — settlements that have a real status)")
for r in q("""
    SELECT d.deal_type, s.status, COUNT(*) AS c
    FROM deals d
    JOIN settlements s ON s.show_id = d.show_id
    GROUP BY d.deal_type, s.status
    ORDER BY d.deal_type, c DESC
"""):
    print(f"  {r['deal_type']:25} {r['status']:15} {r['c']}")

print("\n--- Nulls in 'structured' deal fields (the README claim of drift) ---")
print("  We expect: structured fields often empty, dealNotesFreetext often populated")
for r in q("""
    SELECT
        COUNT(*) AS total_deals,
        SUM(CASE WHEN guarantee_amount IS NULL THEN 1 ELSE 0 END) AS null_guarantee,
        SUM(CASE WHEN percentage IS NULL THEN 1 ELSE 0 END) AS null_percentage,
        SUM(CASE WHEN percentage_basis IS NULL THEN 1 ELSE 0 END) AS null_percentage_basis,
        SUM(CASE WHEN expense_cap IS NULL THEN 1 ELSE 0 END) AS null_expense_cap,
        SUM(CASE WHEN hospitality_cap IS NULL THEN 1 ELSE 0 END) AS null_hospitality_cap,
        SUM(CASE WHEN bonuses_json IS NULL THEN 1 ELSE 0 END) AS null_bonuses_json,
        SUM(CASE WHEN deal_notes_freetext IS NULL OR deal_notes_freetext = '' THEN 1 ELSE 0 END) AS null_freetext
    FROM deals
"""):
    print(json.dumps(r, indent=2))

print("\n--- Recoups: how many settlements have recoupsJson populated? ---")
for r in q("""
    SELECT
        COUNT(*) AS total,
        SUM(CASE WHEN recoups_json IS NULL OR recoups_json = '' OR recoups_json = '[]' THEN 0 ELSE 1 END) AS with_recoups
    FROM settlements
"""):
    print(json.dumps(r, indent=2))
