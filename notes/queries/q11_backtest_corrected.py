"""
Q11 — Corrected backtest with Wednesday-honest signals only.

Replaces Q07's signals (ii) and (iii), which used post-settlement and
post-show-day data respectively, with predictive variants that use ONLY
data available 4 days before the show.

Honest Wednesday-knowable signals:
  (i)       Ambiguous prose          — reads deal_notes_freetext (always)
  (ii.pred) Recoup risk from history — uses prior settlements (always)
  (iii.pred) Hospitality overrun history — same
  (iv)      Ignored structure        — reads bonuses_json (always)
  (v)       Prior open-loop notes    — reads prior settlements.notes (always)

Signal (vi) "agent not confirmed" doesn't apply in backtest because we
don't have agent_confirmed_at in the historical seed; it's a production
signal we'll add when we ship.
"""
import sqlite3, os, json, re
from collections import defaultdict

DB = os.path.join(os.path.dirname(__file__), "..", "..", "data", "greenroom.db")
TODAY = "2026-05-22"  # for "current date" framing — backtest uses each show's own date
conn = sqlite3.connect(DB)
conn.row_factory = sqlite3.Row

def q(sql, *params):
    return [dict(r) for r in conn.execute(sql, params).fetchall()]

def section(t):
    print("\n" + "=" * 78); print(t); print("=" * 78)


# ----------------------------- SIGNALS ---------------------------------------

def signal_i_ambiguous_prose(deal):
    """Wednesday-honest: regex over deal_notes_freetext (always present)."""
    txt = (deal["deal_notes_freetext"] or "").lower()
    patterns = [
        (r"(marketing|promo|spotify|ad spend|boost).{0,40}recoup",
         "marketing recoup mentioned in prose"),
        (r"recoup.{0,30}(against|off|from).{0,10}gross",
         "recoup against gross (ambiguous ordering)"),
        (r"walkout(?!.{0,40}\$)",
         "walkout mentioned without nearby $ threshold"),
        (r"updated|amended|renegotiated|confirm before|note:",
         "amendment hint in prose (structured fields may be stale)"),
    ]
    for pat, desc in patterns:
        if re.search(pat, txt):
            return desc
    return None


def signal_ii_pred_recoup_risk(deal, artist_id, agent_id, show_date):
    """
    Wednesday-honest PREDICTIVE: deal prose mentions no recoup category,
    but the artist OR agent OR agency has a strong history of recoups
    appearing at settlement. Predicts the surprise.
    """
    recoup_words = ["recoup", "marketing", "ad spend", "promo", "spotify",
                    "boost", "instagram", "advance", "rider", "overage", "production"]
    txt = (deal["deal_notes_freetext"] or "").lower()
    if any(w in txt for w in recoup_words):
        return None  # not silent

    # Past 18 months for this artist OR agent (covers cross-agent within agency
    # imperfectly — production version should also join by agency_id)
    hist = q("""
        SELECT COUNT(*) AS shows,
               SUM(CASE WHEN s.recoups_json NOT IN ('','[]') AND s.recoups_json IS NOT NULL
                        THEN 1 ELSE 0 END) AS with_recoup
        FROM settlements s
        JOIN shows sh ON sh.id = s.show_id
        JOIN artists a ON a.id = sh.artist_id
        WHERE (a.id = ? OR a.agent_id = ?)
          AND sh.date < ?
          AND sh.date >= date(?, '-18 months')
    """, artist_id, agent_id, show_date, show_date)[0]

    if hist["shows"] >= 3 and (hist["with_recoup"] / hist["shows"]) >= 0.40:
        return (f"history: {hist['with_recoup']} of last {hist['shows']} shows "
                f"with this artist/agent had a recoup at settlement; this deal silent")
    return None


def signal_iii_pred_hosp_risk(deal, artist_id, agent_id, show_date):
    """
    Wednesday-honest PREDICTIVE: this deal has a hospitality cap, and the
    artist OR agent's prior shows historically overran their hospitality
    caps. Predicts a likely overrun.
    """
    if deal["hospitality_cap"] is None:
        return None

    hist = q("""
        SELECT sh.id AS show_id, d.hospitality_cap, sh.date
        FROM shows sh
        JOIN deals d ON d.show_id = sh.id
        JOIN artists a ON a.id = sh.artist_id
        WHERE (a.id = ? OR a.agent_id = ?)
          AND sh.date < ?
          AND sh.date >= date(?, '-18 months')
          AND d.hospitality_cap IS NOT NULL
    """, artist_id, agent_id, show_date, show_date)

    if len(hist) < 2:
        return None

    overruns = 0
    for h in hist:
        actual = q("""SELECT COALESCE(SUM(amount), 0) AS amt FROM expenses
                      WHERE show_id = ? AND category = 'hospitality'""", h["show_id"])[0]["amt"]
        if actual > h["hospitality_cap"] * 1.1:
            overruns += 1
    if overruns / len(hist) >= 0.5:
        return (f"history: {overruns}/{len(hist)} prior shows by this artist/agent "
                f"overran hospitality cap. This show has cap ${deal['hospitality_cap']}.")
    return None


def signal_iv_ignored_structure(deal):
    """Wednesday-honest: bonuses_json + freetext (both always available)."""
    if deal["bonuses_json"]:
        try:
            for b in json.loads(deal["bonuses_json"]):
                if b.get("type") == "tier_ratchet":
                    return "deal has tier_ratchet in bonuses_json; engine ignores it"
        except Exception:
            pass
    txt = (deal["deal_notes_freetext"] or "").lower()
    if "walkout" in txt: return "walkout pot in prose; not representable in schema"
    if "ratchet" in txt or "escalator" in txt: return "ratchet/escalator in prose"
    return None


def signal_v_prior_open_loop(artist_id, agent_id, show_date):
    """Wednesday-honest: prior settlements.notes (historical, always available)."""
    txt_patterns = ["outstanding", "haven't gotten back", "never resolved", "not yet been pushed back"]
    rows = q("""
        SELECT s.notes, sh.date FROM settlements s
        JOIN shows sh ON sh.id = s.show_id
        JOIN artists a ON a.id = sh.artist_id
        WHERE (a.id = ? OR a.agent_id = ?) AND sh.date < ?
          AND s.notes IS NOT NULL
    """, artist_id, agent_id, show_date)
    for r in rows:
        n = (r["notes"] or "").lower()
        for p in txt_patterns:
            if p in n:
                return f"prior open-loop note ({r['date']}): contains '{p}'"
    return None


# ----------------------------- BACKTEST --------------------------------------

def fires(row):
    s = [
        signal_i_ambiguous_prose(row),
        signal_ii_pred_recoup_risk(row, row["artist_id"], row["agent_id"], row["date"]),
        signal_iii_pred_hosp_risk(row, row["artist_id"], row["agent_id"], row["date"]),
        signal_iv_ignored_structure(row),
        signal_v_prior_open_loop(row["artist_id"], row["agent_id"], row["date"]),
    ]
    return s

def base_query(status_in):
    placeholders = ",".join("?" * len(status_in))
    return q(f"""
        SELECT sh.id AS show_id, sh.date, a.id AS artist_id, a.agent_id, a.name AS artist_name,
               d.deal_type, d.guarantee_amount, d.percentage, d.percentage_basis,
               d.expense_cap, d.hospitality_cap, d.bonuses_json, d.deal_notes_freetext,
               s.status, s.recoups_json, s.notes
        FROM settlements s
        JOIN shows sh ON sh.id = s.show_id
        JOIN artists a ON a.id = sh.artist_id
        JOIN deals d ON d.show_id = sh.id
        WHERE s.status IN ({placeholders})
        ORDER BY sh.date
    """, *status_in)

# ---------------------------------------------------------------------------
section("CORRECTED BACKTEST — Wednesday-honest signals only")
# ---------------------------------------------------------------------------

disputed = base_query(["disputed"])
paid = base_query(["paid", "finalized"])

per_signal_disputed = defaultdict(int)
per_signal_paid = defaultdict(int)
any_d = 0
any_p = 0

print(f"\n  Running 5 Wednesday-honest signals against {len(disputed)} disputes:\n")
for d in disputed:
    s_results = fires(d)
    labels = ["i_ambiguous", "ii_recoup_history", "iii_hosp_history", "iv_structure", "v_open_loop"]
    fired = [(lbl, s) for lbl, s in zip(labels, s_results) if s]
    if fired:
        any_d += 1
        for lbl, _ in fired:
            per_signal_disputed[lbl] += 1
        print(f"    [{d['date']}] {d['artist_name'][:22]:22}  {d['deal_type']:18}  ✓ {len(fired)} signal(s)")
        for lbl, why in fired:
            print(f"          - ({lbl}) {why}")
    else:
        print(f"    [{d['date']}] {d['artist_name'][:22]:22}  {d['deal_type']:18}  ✗ MISS")

for p in paid:
    s_results = fires(p)
    labels = ["i_ambiguous", "ii_recoup_history", "iii_hosp_history", "iv_structure", "v_open_loop"]
    fired = [s for s in s_results if s]
    if fired:
        any_p += 1
        for i, s in enumerate(s_results):
            if s:
                per_signal_paid[labels[i]] += 1

print(f"\n  Per-signal coverage on DISPUTES (recall by signal):")
for lbl in ["i_ambiguous", "ii_recoup_history", "iii_hosp_history", "iv_structure", "v_open_loop"]:
    h = per_signal_disputed[lbl]
    print(f"    {lbl:22} {h}/{len(disputed)} = {100*h/len(disputed):.0f}%")

print(f"\n  Per-signal fire-rate on PAID/FINALIZED (1 - specificity):")
for lbl in ["i_ambiguous", "ii_recoup_history", "iii_hosp_history", "iv_structure", "v_open_loop"]:
    h = per_signal_paid[lbl]
    print(f"    {lbl:22} {h}/{len(paid)} = {100*h/len(paid):.0f}%")

# Confusion matrix for "any signal fires"
TP = any_d
FN = len(disputed) - any_d
FP = any_p
TN = len(paid) - any_p
print(f"\n  Combined 'any signal fires' confusion matrix:")
print(f"    TP={TP}  FN={FN}  FP={FP}  TN={TN}")
print(f"    Recall    = {TP}/({TP}+{FN}) = {100*TP/(TP+FN):.1f}%")
print(f"    Precision = {TP}/({TP}+{FP}) = {100*TP/(TP+FP):.1f}%")
print(f"    Fire-rate on paid: {FP}/{len(paid)} = {100*FP/len(paid):.1f}%")

# Sanity: compare to original Q07 baseline
print(f"\n  Comparison to original (mixed) Q07 baseline:")
print(f"    Q07 (audit-OK signals included):  recall 54.2%, precision 6.7%")
print(f"    Q11 Wednesday-honest only:        recall {100*TP/(TP+FN):.1f}%, precision {100*TP/(TP+FP):.1f}%")
