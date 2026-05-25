"""
Q07 — Build-prep + offline backtest.

Sections:
  (a) Prose corpus analysis — length distribution, vocabulary patterns.
      Informs LLM extraction prompt design.
  (b) Eval set candidate selection — ~15 shows spanning complexity, agency,
      outcome. Hand-labelable for extraction evals.
  (c) "Today view": what the Wednesday pre-flight would show on 2026-05-22.
      Uses un-filtered DB read (does NOT re-implement the lib/queries.ts bug).
  (d) Offline backtest — for each of the 24 historically disputed shows,
      do signals (i)–(v) fire? Coverage % per signal. Headline memo number.
  (e) Agent-level dispute patterns — what each agent fights about.
  (f) Math reconciliation: dealMath.ts output vs settlement.total_to_artist
      for the deal types the engine claims to handle.
"""
import sqlite3, os, json, re, statistics
from collections import Counter, defaultdict

DB = os.path.join(os.path.dirname(__file__), "..", "..", "data", "greenroom.db")
TODAY = "2026-05-22"
conn = sqlite3.connect(DB)
conn.row_factory = sqlite3.Row

def q(sql, *params):
    return [dict(r) for r in conn.execute(sql, params).fetchall()]

def section(t):
    print("\n" + "=" * 78); print(t); print("=" * 78)

# =============================================================================
section("(a) Prose corpus analysis — deal_notes_freetext")
# =============================================================================
rows = q("SELECT deal_notes_freetext, deal_type FROM deals WHERE deal_notes_freetext IS NOT NULL")
lengths = [len(r["deal_notes_freetext"]) for r in rows]
print(f"  Deals with freetext: {len(rows)} (100%)")
print(f"  Length percentiles (chars):")
print(f"    min: {min(lengths)}, p25: {statistics.quantiles(lengths, n=4)[0]:.0f}, "
      f"median: {statistics.median(lengths):.0f}, "
      f"p75: {statistics.quantiles(lengths, n=4)[2]:.0f}, max: {max(lengths)}")

# Vocabulary patterns — what phrases recur?
patterns = [
    ("vs / versus", r"\bvs\.?\b|versus"),
    ("guarantee/g'tee", r"\b(g[\'']?tee|guarantee|guar)\b"),
    ("net", r"\bnet\b"),
    ("gross", r"\bgross\b"),
    ("walkout/walk-out", r"walk[- ]?out"),
    ("ratchet/escalator", r"ratchet|escalator|escalates"),
    ("tier/tiered", r"\btier(ed|s)?\b"),
    ("expense cap", r"expense\s*cap|exp(?:enses?)?\s*cap(?:ped)?"),
    ("hospitality cap/hosp", r"hospitality|hosp\b"),
    ("sellout/sell-out", r"sell[- ]?out"),
    ("recoup", r"recoup"),
    ("marketing", r"marketing|mkt\b"),
    ("if gross/if attendance", r"if\s*(gross|attendance|sold)"),
    ("comp/comps", r"\bcomp(s|ed)?\b"),
    ("door", r"\bdoor\b"),
    ("buyout", r"buyout"),
    ("amendment hint", r"updated|amended|renegotiated|note:|confirm before"),
]
for label, pat in patterns:
    c = sum(1 for r in rows if re.search(pat, r["deal_notes_freetext"], re.IGNORECASE))
    print(f"    {label:30} {c:4} / {len(rows)}  ({100*c/len(rows):.0f}%)")

# =============================================================================
section("(b) Eval set — 15 candidate shows for hand-labeling")
# =============================================================================
# Selection criteria:
#  - Coastal Spell dispute (canonical, the brief's example)
#  - Briar Road (our 2nd hero — D9)
#  - Wet Cement 2026-06-17 (paid-but-disputed-recoup — D8)
#  - The 2 hidden future disputes (Sunday Drivers 2026-07-01, House of Lights 2026-06-10)
#  - A clean flat (no bonus, no recoup)
#  - A clean % of gross
#  - A vs-net with ratchet in bonuses_json
#  - A vs-net with walkout pot in prose
#  - A vs-gross variant
#  - A door deal
#  - A complex Paradigm deal (highest complex-prose rate)
#  - A Wasserman deal (highest dispute rate)
#  - A WME deal (lowest rate, sanity)
#  - A deal with structured amendment in prose ("Updated 4 days before show")

candidates = [
    ("show_coastal_spell_dispute", "Coastal Spell 2025-03-14 — brief's canonical dispute"),
    ("show_0007", "Briar Road 2024-10-16 — 2nd hero, has 'confirm before settlement' note in prose"),
    ("show_0001", "Wet Cement 2026-06-17 — paid-but-disputed-recoup (D8)"),
]

# The 2 hidden future disputes
rows = q("""
    SELECT sh.id, sh.date, a.name AS artist
    FROM shows sh
    JOIN artists a ON a.id = sh.artist_id
    JOIN settlements s ON s.show_id = sh.id
    WHERE sh.date > ? AND s.status = 'disputed'
""", TODAY)
for r in rows:
    candidates.append((r["id"], f"{r['artist']} {r['date']} — hidden future dispute (demo case)"))

# A clean flat (no bonus, no recoup, no expense cap drama)
rows = q("""
    SELECT sh.id, sh.date, a.name AS artist, d.deal_notes_freetext
    FROM deals d
    JOIN shows sh ON sh.id = d.show_id
    JOIN artists a ON a.id = sh.artist_id
    JOIN settlements s ON s.show_id = sh.id
    WHERE d.deal_type = 'flat'
      AND d.bonuses_json IS NULL
      AND s.status = 'paid'
      AND (s.recoups_json IS NULL OR s.recoups_json = '' OR s.recoups_json = '[]')
      AND LENGTH(d.deal_notes_freetext) < 80
    LIMIT 1
""")
if rows:
    candidates.append((rows[0]["id"], f"{rows[0]['artist']} {rows[0]['date']} — clean flat baseline"))

# A clean % of gross
rows = q("""
    SELECT sh.id, sh.date, a.name AS artist
    FROM deals d
    JOIN shows sh ON sh.id = d.show_id
    JOIN artists a ON a.id = sh.artist_id
    JOIN settlements s ON s.show_id = sh.id
    WHERE d.deal_type = 'percentage_of_gross' AND s.status = 'paid'
    LIMIT 1
""")
if rows:
    candidates.append((rows[0]["id"], f"{rows[0]['artist']} {rows[0]['date']} — % of gross baseline"))

# A vs-net with ratchet in bonuses_json
rows = q("""
    SELECT sh.id, sh.date, a.name AS artist
    FROM deals d
    JOIN shows sh ON sh.id = d.show_id
    JOIN artists a ON a.id = sh.artist_id
    WHERE d.deal_type = 'vs' AND d.percentage_basis = 'net'
      AND d.bonuses_json LIKE '%tier_ratchet%'
    LIMIT 1
""")
if rows:
    candidates.append((rows[0]["id"], f"{rows[0]['artist']} {rows[0]['date']} — vs-net with tier ratchet"))

# A vs-net with walkout pot
rows = q("""
    SELECT sh.id, sh.date, a.name AS artist
    FROM deals d
    JOIN shows sh ON sh.id = d.show_id
    JOIN artists a ON a.id = sh.artist_id
    WHERE d.deal_type = 'vs' AND d.deal_notes_freetext LIKE '%walkout%'
    LIMIT 1
""")
if rows:
    candidates.append((rows[0]["id"], f"{rows[0]['artist']} {rows[0]['date']} — vs with walkout pot"))

# A vs-gross variant
rows = q("""
    SELECT sh.id, sh.date, a.name AS artist
    FROM deals d
    JOIN shows sh ON sh.id = d.show_id
    JOIN artists a ON a.id = sh.artist_id
    WHERE d.deal_type = 'vs' AND d.percentage_basis = 'gross'
    LIMIT 1
""")
if rows:
    candidates.append((rows[0]["id"], f"{rows[0]['artist']} {rows[0]['date']} — vs-gross variant"))

# Door deal
rows = q("""
    SELECT sh.id, sh.date, a.name AS artist
    FROM deals d
    JOIN shows sh ON sh.id = d.show_id
    JOIN artists a ON a.id = sh.artist_id
    WHERE d.deal_type = 'door'
    LIMIT 1
""")
if rows:
    candidates.append((rows[0]["id"], f"{rows[0]['artist']} {rows[0]['date']} — door deal"))

# A complex Paradigm vs deal
rows = q("""
    SELECT sh.id, sh.date, a.name AS artist
    FROM deals d
    JOIN shows sh ON sh.id = d.show_id
    JOIN artists a ON a.id = sh.artist_id
    JOIN agents ag2 ON ag2.id = a.agent_id
    JOIN agencies ag ON ag.id = ag2.agency_id
    WHERE d.deal_type = 'vs' AND ag.name = 'Paradigm'
      AND d.deal_notes_freetext LIKE '%ratchet%'
    LIMIT 1
""")
if rows:
    candidates.append((rows[0]["id"], f"{rows[0]['artist']} {rows[0]['date']} — Paradigm complex vs"))

# A Wasserman dispute
rows = q("""
    SELECT sh.id, sh.date, a.name AS artist
    FROM settlements s
    JOIN shows sh ON sh.id = s.show_id
    JOIN artists a ON a.id = sh.artist_id
    JOIN agents ag2 ON ag2.id = a.agent_id
    JOIN agencies ag ON ag.id = ag2.agency_id
    WHERE s.status = 'disputed' AND ag.name = 'Wasserman'
    LIMIT 1
""")
if rows:
    candidates.append((rows[0]["id"], f"{rows[0]['artist']} {rows[0]['date']} — Wasserman dispute"))

# A WME dispute (other than Coastal Spell)
rows = q("""
    SELECT sh.id, sh.date, a.name AS artist
    FROM settlements s
    JOIN shows sh ON sh.id = s.show_id
    JOIN artists a ON a.id = sh.artist_id
    JOIN agents ag2 ON ag2.id = a.agent_id
    JOIN agencies ag ON ag.id = ag2.agency_id
    WHERE s.status = 'disputed' AND ag.name = 'WME'
      AND sh.id != 'show_coastal_spell_dispute'
    LIMIT 1
""")
if rows:
    candidates.append((rows[0]["id"], f"{rows[0]['artist']} {rows[0]['date']} — WME dispute (not Coastal Spell)"))

# Dedupe
seen = set()
final = []
for id_, label in candidates:
    if id_ not in seen:
        final.append((id_, label))
        seen.add(id_)
print(f"  Eval set size: {len(final)}")
for id_, label in final:
    print(f"    {id_:40}  {label}")

# Output the eval set as JSON for the build to consume
eval_path = os.path.join(os.path.dirname(__file__), "..", "eval_set_candidates.json")
with open(eval_path, "w", encoding="utf-8") as f:
    full = []
    for id_, label in final:
        deal = q("""
            SELECT sh.id AS show_id, sh.date, a.name AS artist, d.deal_type,
                   d.guarantee_amount, d.percentage, d.percentage_basis,
                   d.expense_cap, d.hospitality_cap, d.bonuses_json,
                   d.deal_notes_freetext, s.status AS sett_status,
                   s.recoups_json, ag.name AS agency
            FROM shows sh
            JOIN artists a ON a.id = sh.artist_id
            JOIN deals d ON d.show_id = sh.id
            LEFT JOIN settlements s ON s.show_id = sh.id
            LEFT JOIN agents ag2 ON ag2.id = a.agent_id
            LEFT JOIN agencies ag ON ag.id = ag2.agency_id
            WHERE sh.id = ?
        """, id_)
        if deal:
            full.append({"label": label, **deal[0]})
    json.dump(full, f, indent=2, default=str)
print(f"\n  Wrote eval-set candidates to: notes/eval_set_candidates.json")

# =============================================================================
section("(c) Today view — what the un-filtered pre-flight would show on 2026-05-22")
# =============================================================================
# Look 14 days ahead (typical advance + settle window)
rows = q("""
    SELECT sh.id, sh.date, a.name AS artist, d.deal_type, d.deal_notes_freetext,
           d.expense_cap, d.hospitality_cap, d.bonuses_json,
           s.status, s.recoups_json, ag.name AS agency, ag2.name AS agent
    FROM shows sh
    JOIN artists a ON a.id = sh.artist_id
    JOIN deals d ON d.show_id = sh.id
    LEFT JOIN settlements s ON s.show_id = sh.id
    LEFT JOIN agents ag2 ON ag2.id = a.agent_id
    LEFT JOIN agencies ag ON ag.id = ag2.agency_id
    WHERE sh.date BETWEEN ? AND date(?, '+14 days')
    ORDER BY sh.date
""", TODAY, TODAY)
print(f"  Shows in next 14 days: {len(rows)}")
for r in rows:
    print(f"\n  [{r['date']}] {r['artist'][:25]:25}  {(r['agency'] or '-')[:12]:12}  deal={r['deal_type']}  sett.status={r['status']}")
    if r["deal_notes_freetext"]:
        print(f"    prose: {r['deal_notes_freetext'][:160]}")

# =============================================================================
section("(d) Offline backtest — would pre-flight signals catch the 24 disputes?")
# =============================================================================
# Define each signal as a function over the deal/expense/settlement data.

def signal_i_ambiguous_prose(deal):
    """Signal (i): freetext contains ambiguous-clause patterns.
    Heuristic baseline; real prototype uses LLM."""
    txt = (deal["deal_notes_freetext"] or "").lower()
    # patterns that historically caused disputes:
    patterns = [
        # marketing/promo recoup without clear inside/outside
        (r"(marketing|promo|spotify|ad spend|boost).{0,40}recoup", "marketing recoup mentioned"),
        (r"recoup.{0,30}(against|off|from).{0,10}gross", "recoup against gross (ambiguous order)"),
        # walkout pot or ratchet with no explicit threshold language
        (r"walkout(?!.{0,40}\$)", "walkout mentioned but no $ threshold"),
        # amendment hints
        (r"updated|amended|renegotiated|confirm before|note:", "deal has amendment hint in prose"),
        # vs deals without clear basis statement
    ]
    for pat, desc in patterns:
        if re.search(pat, txt):
            return desc
    return None

def signal_ii_silent_recoup(deal, settlement):
    """Signal (ii): settlement has a recoup category the deal prose doesn't mention."""
    txt = (deal["deal_notes_freetext"] or "").lower()
    if not settlement or not settlement.get("recoups_json"):
        return None
    try:
        recoups = json.loads(settlement["recoups_json"])
    except Exception:
        return None
    if not recoups:
        return None
    kw_map = {
        "marketing": ["marketing", "recoup", "ad spend", "promo", "spotify", "boost", "instagram"],
        "hospitality_overage": ["hospitality", "rider", "overage"],
        "production_overage": ["production", "tech rider", "overage"],
        "prior_advance": ["advance", "prior"],
        "damages": ["damages", "damage"],
    }
    surprises = []
    for rcp in recoups:
        cat = rcp.get("category")
        kws = kw_map.get(cat, [])
        if not kws:
            continue
        mentioned = any(k in txt for k in kws)
        if not mentioned:
            surprises.append(f"{cat} (${rcp.get('amount', 0):.0f})")
    if surprises:
        return f"surprise recoup(s): {', '.join(surprises)}"
    return None

def signal_iii_hospitality_overrun(deal, expenses):
    """Signal (iii): actual hospitality > hospitality_cap by >10%."""
    if deal["hospitality_cap"] is None:
        return None
    actual = sum(e["amount"] for e in expenses if e["category"] == "hospitality")
    if actual > deal["hospitality_cap"] * 1.1:
        return f"hospitality ${actual:.0f} > cap ${deal['hospitality_cap']:.0f} ({100*actual/deal['hospitality_cap']:.0f}%)"
    return None

def signal_iv_ignored_structure(deal):
    """Signal (iv): deal has tier_ratchet in bonuses_json (engine ignores)
    OR prose mentions complex structure not represented."""
    if deal["bonuses_json"]:
        try:
            for b in json.loads(deal["bonuses_json"]):
                if b.get("type") == "tier_ratchet":
                    return "deal has tier_ratchet that in-app engine ignores"
        except Exception:
            pass
    txt = (deal["deal_notes_freetext"] or "").lower()
    if "walkout" in txt:
        return "deal has walkout pot in prose, not in schema"
    if "ratchet" in txt or "escalator" in txt:
        return "deal has ratchet/escalator in prose"
    return None

def signal_v_prior_open_loop(artist_id, agent_id, show_date):
    """Signal (v): same agent or artist has a prior settlement with open-loop notes."""
    txt_patterns = ["outstanding", "haven't gotten back", "never resolved", "not yet been pushed back"]
    rows = q("""
        SELECT s.notes, sh.date
        FROM settlements s
        JOIN shows sh ON sh.id = s.show_id
        JOIN artists a ON a.id = sh.artist_id
        WHERE (a.id = ? OR a.agent_id = ?)
          AND sh.date < ?
          AND s.notes IS NOT NULL
    """, artist_id, agent_id, show_date)
    for r in rows:
        n = (r["notes"] or "").lower()
        for p in txt_patterns:
            if p in n:
                return f"prior open-loop note on {r['date']}"
    return None

# Run backtest across ALL 24 disputed shows
disputed = q("""
    SELECT sh.id AS show_id, sh.date, a.id AS artist_id, a.name AS artist_name,
           a.agent_id, d.dealType AS unused, d.deal_type, d.guarantee_amount,
           d.percentage, d.percentage_basis, d.expense_cap, d.hospitality_cap,
           d.bonuses_json, d.deal_notes_freetext,
           s.status, s.recoups_json, s.notes
    FROM settlements s
    JOIN shows sh ON sh.id = s.show_id
    JOIN artists a ON a.id = sh.artist_id
    JOIN deals d ON d.show_id = sh.id
    WHERE s.status = 'disputed'
    ORDER BY sh.date
""") if False else q("""
    SELECT sh.id AS show_id, sh.date, a.id AS artist_id, a.name AS artist_name,
           a.agent_id, d.deal_type, d.guarantee_amount,
           d.percentage, d.percentage_basis, d.expense_cap, d.hospitality_cap,
           d.bonuses_json, d.deal_notes_freetext,
           s.status, s.recoups_json, s.notes
    FROM settlements s
    JOIN shows sh ON sh.id = s.show_id
    JOIN artists a ON a.id = sh.artist_id
    JOIN deals d ON d.show_id = sh.id
    WHERE s.status = 'disputed'
    ORDER BY sh.date
""")

signal_hits = defaultdict(int)
any_signal_hits = 0
print(f"  Backtest against {len(disputed)} historically disputed shows:")
print(f"  (heuristic baseline — real prototype's LLM signal will be stronger on (i))\n")
for d in disputed:
    expenses = q("SELECT category, amount FROM expenses WHERE show_id = ?", d["show_id"])
    settlement = {"recoups_json": d["recoups_json"], "notes": d["notes"]}
    s1 = signal_i_ambiguous_prose(d)
    s2 = signal_ii_silent_recoup(d, settlement)
    s3 = signal_iii_hospitality_overrun(d, expenses)
    s4 = signal_iv_ignored_structure(d)
    s5 = signal_v_prior_open_loop(d["artist_id"], d["agent_id"], d["date"])
    fired = [s for s in [s1, s2, s3, s4, s5] if s]
    if s1: signal_hits["i_ambiguous_prose"] += 1
    if s2: signal_hits["ii_silent_recoup"] += 1
    if s3: signal_hits["iii_hosp_overrun"] += 1
    if s4: signal_hits["iv_ignored_structure"] += 1
    if s5: signal_hits["v_prior_open_loop"] += 1
    if fired: any_signal_hits += 1
    if fired:
        print(f"    [{d['date']}] {d['artist_name'][:22]:22}  {d['deal_type']:18}  fired: {len(fired)} signal(s)")
        for f in fired:
            print(f"      - {f}")
    else:
        print(f"    [{d['date']}] {d['artist_name'][:22]:22}  {d['deal_type']:18}  NO SIGNAL FIRED <-- miss")
print(f"\n  Coverage summary:")
for sig, n in signal_hits.items():
    print(f"    {sig:25} {n}/{len(disputed)} = {100*n/len(disputed):.0f}%")
print(f"    ANY signal fired:         {any_signal_hits}/{len(disputed)} = {100*any_signal_hits/len(disputed):.0f}%")

# Precision: same signals on non-disputed shows
section("(d.2) Precision — would the signals over-fire on the paid 447?")
paid = q("""
    SELECT sh.id AS show_id, sh.date, a.id AS artist_id, a.agent_id,
           d.deal_type, d.expense_cap, d.hospitality_cap, d.bonuses_json,
           d.deal_notes_freetext, s.recoups_json, s.notes
    FROM settlements s
    JOIN shows sh ON sh.id = s.show_id
    JOIN artists a ON a.id = sh.artist_id
    JOIN deals d ON d.show_id = sh.id
    WHERE s.status IN ('paid', 'finalized')
""")
paid_signal_hits = defaultdict(int)
paid_any = 0
for d in paid:
    expenses = q("SELECT category, amount FROM expenses WHERE show_id = ?", d["show_id"])
    settlement = {"recoups_json": d["recoups_json"], "notes": d["notes"]}
    s1 = signal_i_ambiguous_prose(d)
    s2 = signal_ii_silent_recoup(d, settlement)
    s3 = signal_iii_hospitality_overrun(d, expenses)
    s4 = signal_iv_ignored_structure(d)
    s5 = signal_v_prior_open_loop(d["artist_id"], d["agent_id"], d["date"])
    fired = [s for s in [s1, s2, s3, s4, s5] if s]
    if s1: paid_signal_hits["i_ambiguous_prose"] += 1
    if s2: paid_signal_hits["ii_silent_recoup"] += 1
    if s3: paid_signal_hits["iii_hosp_overrun"] += 1
    if s4: paid_signal_hits["iv_ignored_structure"] += 1
    if s5: paid_signal_hits["v_prior_open_loop"] += 1
    if fired: paid_any += 1
print(f"  Fire-rate on paid/finalized (n={len(paid)}):")
for sig, n in paid_signal_hits.items():
    print(f"    {sig:25} {n}/{len(paid)} = {100*n/len(paid):.0f}%")
print(f"    ANY signal fired:         {paid_any}/{len(paid)} = {100*paid_any/len(paid):.0f}%")

# Precision = TP / (TP+FP) — treating dispute as positive, paid/finalized as negative
TP = any_signal_hits
FP = paid_any
FN = len(disputed) - any_signal_hits
print(f"\n  If we treat 'any signal fires' as the alarm:")
print(f"    Precision: {TP}/({TP}+{FP}) = {100*TP/(TP+FP):.1f}%")
print(f"    Recall:    {TP}/({TP}+{FN}) = {100*TP/(TP+FN):.1f}%")
print(f"    (Recall is the one we care about — we want to catch the disputes.)")

# =============================================================================
section("(e) Agent-level dispute patterns — what each agent fights about")
# =============================================================================
rows = q("""
    SELECT ag.name AS agency, ag2.name AS agent, COUNT(*) AS disputes,
           s.recoups_json, s.notes, sh.date, a.name AS artist
    FROM settlements s
    JOIN shows sh ON sh.id = s.show_id
    JOIN artists a ON a.id = sh.artist_id
    JOIN agents ag2 ON ag2.id = a.agent_id
    LEFT JOIN agencies ag ON ag.id = ag2.agency_id
    WHERE s.status IN ('disputed','revised','finalized')
    GROUP BY ag.name, ag2.name, sh.id
    ORDER BY ag.name
""")
by_agent = defaultdict(lambda: defaultdict(int))
for r in rows:
    key = f"{r['agency']}/{r['agent']}"
    if not r["recoups_json"]:
        by_agent[key]["no_recoup_dispute"] += 1
        continue
    try:
        rs = json.loads(r["recoups_json"])
        for x in rs:
            if x.get("status") == "disputed":
                by_agent[key][x.get("category", "?")] += 1
    except Exception:
        pass
print(f"  Dispute categories by agent (where recoup-level dispute is recorded):")
for k, v in sorted(by_agent.items(), key=lambda x: -sum(x[1].values())):
    if sum(v.values()) >= 2:
        print(f"    {k:35} {dict(v)}")

# =============================================================================
section("(f) Math reconciliation — dealMath.ts output vs settlement.total_to_artist")
# =============================================================================
# Engine claims to handle flat and percentage_of_gross.
# For flat: total_to_artist should equal guarantee + sellout bonus (if any).
# For pct of gross: total_to_artist = gross * pct (+ bonuses).
rows = q("""
    SELECT sh.id AS show_id, sh.date, a.name AS artist, d.deal_type,
           d.guarantee_amount, d.percentage, d.bonuses_json,
           t.gross, t.qty,
           s.total_to_artist, s.status
    FROM settlements s
    JOIN shows sh ON sh.id = s.show_id
    JOIN artists a ON a.id = sh.artist_id
    JOIN deals d ON d.show_id = sh.id
    LEFT JOIN ticket_sales t ON t.show_id = sh.id
    WHERE d.deal_type IN ('flat', 'percentage_of_gross')
""")
print(f"  Engine-supported deals: {len(rows)}")
mismatches = 0
for r in rows:
    if r["deal_type"] == "flat":
        expected = r["guarantee_amount"] or 0
        # add sellout bonus if applies (assume 650 capacity, >=95%)
        if r["bonuses_json"]:
            try:
                for b in json.loads(r["bonuses_json"]):
                    if b.get("type") == "sellout" and r["qty"] and r["qty"] >= 0.95 * 650:
                        expected += b.get("amount", 0)
                    if b.get("type") == "gross_threshold" and r["gross"] and r["gross"] >= b.get("threshold", 0):
                        expected += b.get("amount", 0)
            except Exception:
                pass
    else:  # pct of gross
        expected = (r["gross"] or 0) * (r["percentage"] or 0)
        if r["bonuses_json"]:
            try:
                for b in json.loads(r["bonuses_json"]):
                    if b.get("type") == "gross_threshold" and r["gross"] and r["gross"] >= b.get("threshold", 0):
                        expected += b.get("amount", 0)
            except Exception:
                pass
    actual = r["total_to_artist"] or 0
    diff = actual - expected
    if abs(diff) > 1:
        mismatches += 1
        if mismatches <= 8:
            print(f"    [{r['date']}] {r['artist'][:22]:22}  {r['deal_type']:20}  "
                  f"expected=${expected:.0f}  actual=${actual:.0f}  diff=${diff:+.0f}")
print(f"\n  Engine-claimed deals where stored total != naive recompute: {mismatches}/{len(rows)}")
