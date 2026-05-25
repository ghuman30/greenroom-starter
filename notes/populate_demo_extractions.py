"""
Populate deals.extracted_deal_json from notes/eval_results.json.

Use this to seed demo extractions into the DB without running live LLM
calls (which need credits + are non-deterministic). Run AFTER an eval
harness run so eval_results.json is current.

Run:
  python -X utf8 notes/populate_demo_extractions.py

Idempotent — re-running overwrites with latest eval results.
"""
import sqlite3, json, os, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "data" / "greenroom.db"
RESULTS = ROOT / "notes" / "eval_results.json"

if not RESULTS.exists():
    print(f"ERROR: {RESULTS} does not exist. Run notes/eval_harness.py first.")
    sys.exit(1)

data = json.loads(RESULTS.read_text(encoding="utf-8"))
conn = sqlite3.connect(DB)
conn.row_factory = sqlite3.Row

# Map show_id -> deal.id (deals table uses its own ids, not show_id)
deals_map = {}
for row in conn.execute("SELECT id, show_id FROM deals").fetchall():
    deals_map[row["show_id"]] = row["id"]

written = 0
skipped_no_output = 0
skipped_no_deal = 0

for case in data.get("results", []):
    sid = case["show_id"]
    out = case.get("actual_output")
    if not out:
        skipped_no_output += 1
        continue
    deal_id = deals_map.get(sid)
    if not deal_id:
        skipped_no_deal += 1
        continue
    # Decorate with metadata if missing
    out.setdefault("model", data.get("model", "unknown"))
    out.setdefault("generated_at", data.get("ran_at", ""))
    out.setdefault("source", "notes")
    conn.execute(
        "UPDATE deals SET extracted_deal_json = ? WHERE id = ?",
        (json.dumps(out), deal_id),
    )
    written += 1
    print(f"  {sid:35} -> deal {deal_id} (model: {out.get('model')})")

conn.commit()
conn.close()

print(f"\nDone.")
print(f"  Written: {written}")
print(f"  Skipped (no LLM output in eval result): {skipped_no_output}")
print(f"  Skipped (no matching deal in DB):       {skipped_no_deal}")
