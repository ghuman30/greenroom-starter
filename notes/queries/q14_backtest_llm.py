"""
Q14 — Re-run the Wednesday-honest backtest with LLM-extracted ambiguity
flags replacing the regex signal (i).

Q11 was the heuristic baseline: 41.7% recall on 24 historical disputes.
Q14 measures the lift from using lib/extraction.ts output (stored in
deals.extracted_deal_json) as the signal (i) source instead of regex
patterns on prose.

This is the headline number for the memo.

Caveat: extractions populated by notes/populate_demo_extractions.py
cover only the 12 eval cases; deals without an extraction get treated
as "no flag fired" for signal (i) — which is *honest* (the LLM hasn't
read them yet) but means the lift here is a *floor*. Running extraction
across the full corpus would reveal the true ceiling.

Run:
  python -X utf8 notes/queries/q14_backtest_llm.py
"""
import sqlite3, os, json, re
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DB = ROOT / "data" / "greenroom.db"
conn = sqlite3.connect(DB)
conn.row_factory = sqlite3.Row

def q(sql, *params):
    return [dict(r) for r in conn.execute(sql, params).fetchall()]

def section(t):
    print("\n" + "=" * 78); print(t); print("=" * 78)

# --------- Reproduce the Q11 signal functions for consistency -----------

def signal_i_regex(deal):
    """Q11 baseline — regex on deal_notes_freetext."""
    txt = (deal["deal_notes_freetext"] or "").lower()
    patterns = [
        r"(marketing|promo|spotify|ad spend|boost).{0,40}recoup",
        r"recoup.{0,30}(against|off|from).{0,10}gross",
        r"walkout(?!.{0,40}\$)",
        r"updated|amended|renegotiated|confirm before|note:",
    ]
    return any(re.search(pat, txt) for pat in patterns)

def signal_i_llm(deal):
    """Q14 upgrade — read ambiguity_flags from LLM extraction."""
    if not deal.get("extracted_deal_json"):
        return False  # honest: no extraction, no signal
    try:
        out = json.loads(deal["extracted_deal_json"])
    except Exception:
        return False
    flags = out.get("ambiguity_flags") or []
    # Fire if any flag is medium or high severity
    return any(f.get("severity") in ("medium", "high") for f in flags)

def signal_ii_pred(deal, artist_id, agent_id, show_date):
    """Unchanged — recoup history."""
    recoup_words = ["recoup","marketing","ad spend","promo","spotify","boost","instagram","advance","rider","overage","production"]
    txt = (deal["deal_notes_freetext"] or "").lower()
    if any(w in txt for w in recoup_words): return False
    hist = q("""
        SELECT COUNT(*) AS shows,
               SUM(CASE WHEN s.recoups_json NOT IN ('','[]') AND s.recoups_json IS NOT NULL THEN 1 ELSE 0 END) AS w
        FROM settlements s
        JOIN shows sh ON sh.id = s.show_id
        JOIN artists a ON a.id = sh.artist_id
        WHERE (a.id = ? OR a.agent_id = ?)
          AND sh.date < ?
          AND sh.date >= date(?, '-18 months')
    """, artist_id, agent_id, show_date, show_date)[0]
    return hist["shows"] >= 3 and (hist["w"] / hist["shows"]) >= 0.40

def signal_iii_pred(deal, artist_id, agent_id, show_date):
    if deal["hospitality_cap"] is None: return False
    hist = q("""
        SELECT sh.id AS show_id, d.hospitality_cap
        FROM shows sh JOIN deals d ON d.show_id = sh.id JOIN artists a ON a.id = sh.artist_id
        WHERE (a.id = ? OR a.agent_id = ?) AND sh.date < ? AND sh.date >= date(?, '-18 months')
          AND d.hospitality_cap IS NOT NULL
    """, artist_id, agent_id, show_date, show_date)
    if len(hist) < 2: return False
    overruns = 0
    for h in hist:
        actual = q("SELECT COALESCE(SUM(amount),0) AS a FROM expenses WHERE show_id=? AND category='hospitality'", h["show_id"])[0]["a"]
        if actual > h["hospitality_cap"] * 1.1: overruns += 1
    return overruns / len(hist) >= 0.5

def signal_iv(deal):
    if deal["bonuses_json"]:
        try:
            for b in json.loads(deal["bonuses_json"]):
                if b.get("type") == "tier_ratchet": return True
        except Exception: pass
    txt = (deal["deal_notes_freetext"] or "").lower()
    return "walkout" in txt or "ratchet" in txt or "escalator" in txt

def signal_v(artist_id, agent_id, show_date):
    pats = ["outstanding", "haven't gotten back", "never resolved", "not yet been pushed back"]
    rows = q("""
        SELECT s.notes FROM settlements s
        JOIN shows sh ON sh.id = s.show_id JOIN artists a ON a.id = sh.artist_id
        WHERE (a.id = ? OR a.agent_id = ?) AND sh.date < ? AND s.notes IS NOT NULL
    """, artist_id, agent_id, show_date)
    return any(p in (r["notes"] or "").lower() for r in rows for p in pats)

# --------- Backtest core ---------

def get_population(status_in):
    placeholders = ",".join("?" * len(status_in))
    return q(f"""
        SELECT sh.id AS show_id, sh.date, a.id AS artist_id, a.agent_id,
               d.deal_type, d.hospitality_cap, d.bonuses_json, d.deal_notes_freetext,
               d.extracted_deal_json
        FROM settlements s
        JOIN shows sh ON sh.id = s.show_id
        JOIN artists a ON a.id = sh.artist_id
        JOIN deals d ON d.show_id = sh.id
        WHERE s.status IN ({placeholders})
    """, *status_in)

def run_backtest(use_llm):
    disputed = get_population(["disputed"])
    paid = get_population(["paid", "finalized"])

    def fires(deal):
        s_i = signal_i_llm(deal) if use_llm else signal_i_regex(deal)
        return any([
            s_i,
            signal_ii_pred(deal, deal["artist_id"], deal["agent_id"], deal["date"]),
            signal_iii_pred(deal, deal["artist_id"], deal["agent_id"], deal["date"]),
            signal_iv(deal),
            signal_v(deal["artist_id"], deal["agent_id"], deal["date"]),
        ])

    TP = sum(1 for d in disputed if fires(d))
    FN = len(disputed) - TP
    FP = sum(1 for d in paid if fires(d))
    TN = len(paid) - FP
    return dict(TP=TP, FN=FN, FP=FP, TN=TN, n_disp=len(disputed), n_paid=len(paid))

# --------- Per-signal recall on disputed (just for signal i) ---------

def per_signal_i_recall():
    disputed = get_population(["disputed"])
    regex_hit = sum(1 for d in disputed if signal_i_regex(d))
    llm_hit = sum(1 for d in disputed if signal_i_llm(d))
    return regex_hit, llm_hit, len(disputed)

# --------- Main ---------

section("Q14 — Backtest WITH LLM-extracted ambiguity (signal i upgrade)")
print()

regex_run = run_backtest(use_llm=False)
llm_run = run_backtest(use_llm=True)

def fmt(run, label):
    recall = 100 * run["TP"] / (run["TP"] + run["FN"])
    precision = 100 * run["TP"] / (run["TP"] + run["FP"]) if (run["TP"] + run["FP"]) > 0 else 0.0
    fire_rate = 100 * run["FP"] / run["n_paid"]
    print(f"  {label}:")
    print(f"    TP={run['TP']}  FN={run['FN']}  FP={run['FP']}  TN={run['TN']}")
    print(f"    Recall    = {run['TP']}/{run['TP']+run['FN']} = {recall:.1f}%")
    print(f"    Precision = {run['TP']}/{run['TP']+run['FP']} = {precision:.1f}%")
    print(f"    Fire-rate on paid: {run['FP']}/{run['n_paid']} = {fire_rate:.1f}%")
    print()

fmt(regex_run, "Q11 baseline (regex signal i)")
fmt(llm_run, "Q14 upgrade  (LLM-extracted ambiguity)")

# Lift on signal (i) alone
r_hit, l_hit, n = per_signal_i_recall()
print(f"  Signal (i) alone:")
print(f"    Regex catches  {r_hit}/{n} = {100*r_hit/n:.1f}%")
print(f"    LLM catches    {l_hit}/{n} = {100*l_hit/n:.1f}%")
print()

# Population with extracted_deal_json
n_extracted = q("SELECT COUNT(*) AS c FROM deals WHERE extracted_deal_json IS NOT NULL AND extracted_deal_json != ''")[0]["c"]
n_all = q("SELECT COUNT(*) AS c FROM deals")[0]["c"]
print(f"  Honesty note: only {n_extracted}/{n_all} deals have an LLM extraction populated")
print(f"  (the 12 eval cases). For the remaining {n_all - n_extracted}, signal (i) defaults to OFF.")
print(f"  Running LLM extraction across the full corpus would raise the LLM-line numbers.")
print()

delta = (100 * llm_run['TP'] / (llm_run['TP'] + llm_run['FN'])) - (100 * regex_run['TP'] / (regex_run['TP'] + regex_run['FN']))
print(f"  Headline lift: total recall +{delta:.1f} percentage points after LLM upgrade")
print(f"  on signal (i), with extraction populated for ~{100*n_extracted/n_all:.0f}% of deals.")
