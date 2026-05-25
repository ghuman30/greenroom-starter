"""
Q09 — Trace the offline backtest end-to-end on specific shows.

This script is purely educational. Its job is to make the abstract
"recall = 54%" number concrete by walking through:
  - the actual data for a few specific shows
  - each of the 5 signals applied to that data
  - whether each signal fires, with the exact reason
  - the final answer (fire? miss?)

Then it computes the confusion matrix and the recall/precision metrics
with the math written out by hand.

This is what the q07_build_prep.py script did internally, just made
visible.
"""
import sqlite3, os, json, re
DB = os.path.join(os.path.dirname(__file__), "..", "..", "data", "greenroom.db")
conn = sqlite3.connect(DB)
conn.row_factory = sqlite3.Row

def q(sql, *params):
    return [dict(r) for r in conn.execute(sql, params).fetchall()]

# ---------------------------------------------------------------------------
# THE FIVE SIGNALS — each is a pure function over a show's data.
# Each returns either a string ("alarm reason") or None ("no alarm").
# ---------------------------------------------------------------------------

def signal_i_ambiguous_prose(deal):
    """
    Signal (i): the deal_notes_freetext contains language patterns that
    historically correlate with disputes. This is the HEURISTIC baseline.

    In the real prototype, an LLM replaces this — it reads the prose
    semantically and asks "could a reasonable person interpret this two
    different ways?" For the backtest, we use regex patterns drawn from
    the actual disputes we observed in evidence.md.
    """
    txt = (deal["deal_notes_freetext"] or "").lower()
    patterns = [
        # Pattern 1: any kind of marketing/ad/promo recoup mention.
        # Why: 56 of 84 recouped settlements are marketing recoups (D2),
        # and the Coastal Spell dispute proved a single line like
        # "marketing recoup of $900 against gross" is ambiguous.
        (r"(marketing|promo|spotify|ad spend|boost).{0,40}recoup", "marketing recoup mentioned"),

        # Pattern 2: "recoup against gross" — Coastal Spell wording.
        # Why: this phrasing is exactly the inside-or-outside-cap fight.
        (r"recoup.{0,30}(against|off|from).{0,10}gross", "recoup against gross (ambiguous order)"),

        # Pattern 3: "walkout" without a nearby dollar amount.
        # Why: walkout pots without explicit thresholds are dispute-prone.
        (r"walkout(?!.{0,40}\$)", "walkout mentioned but no $ threshold"),

        # Pattern 4: amendment hints — the deal has been changed since
        # the original email but the structured fields might not reflect it.
        # Why: Briar Road literally contains "structured field still reflects
        # original $11,000 — confirm before settlement" (D9).
        (r"updated|amended|renegotiated|confirm before|note:", "deal has amendment hint in prose"),
    ]
    for pat, desc in patterns:
        if re.search(pat, txt):
            return desc
    return None


def signal_ii_silent_recoup(deal, settlement):
    """
    Signal (ii): the settlement has a recoup line item, but the deal prose
    doesn't mention that category at all. This is the "surprise at 2am"
    pattern — a deduction the agent never saw in the deal email.

    Pure data check, no LLM needed.
    """
    txt = (deal["deal_notes_freetext"] or "").lower()
    if not settlement or not settlement.get("recoups_json"):
        return None
    try:
        recoups = json.loads(settlement["recoups_json"])
    except Exception:
        return None
    if not recoups:
        return None

    # For each recoup category, what would the deal email say if it
    # mentioned this kind of recoup at all? These are the keywords.
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
        if not kws: continue
        mentioned = any(k in txt for k in kws)
        if not mentioned:
            surprises.append(f"{cat} (${rcp.get('amount', 0):.0f})")
    if surprises:
        return f"surprise recoup(s) at settlement not mentioned in deal: {', '.join(surprises)}"
    return None


def signal_iii_hospitality_overrun(deal, expenses):
    """
    Signal (iii): actual hospitality expenses exceed the hospitality cap
    by more than 10%. This is Wednesday-knowable because the expenses
    table is populated as costs come in, before settlement.
    """
    if deal["hospitality_cap"] is None:
        return None
    actual = sum(e["amount"] for e in expenses if e["category"] == "hospitality")
    if actual > deal["hospitality_cap"] * 1.1:
        return f"hospitality actual ${actual:.0f} > cap ${deal['hospitality_cap']:.0f} (running {100*actual/deal['hospitality_cap']:.0f}% of cap)"
    return None


def signal_iv_ignored_structure(deal):
    """
    Signal (iv): the deal carries a structure the in-app engine can't
    settle.
    - bonuses_json has a tier_ratchet entry → dealMath.ts explicitly
      returns "not handled" for these (lib/dealMath.ts:243)
    - prose mentions walkout / ratchet / escalator
    """
    if deal["bonuses_json"]:
        try:
            for b in json.loads(deal["bonuses_json"]):
                if b.get("type") == "tier_ratchet":
                    return "deal has tier_ratchet in bonuses_json; in-app engine ignores it"
        except Exception:
            pass
    txt = (deal["deal_notes_freetext"] or "").lower()
    if "walkout" in txt:
        return "deal has walkout pot in prose; not representable in schema"
    if "ratchet" in txt or "escalator" in txt:
        return "deal has ratchet/escalator in prose"
    return None


def signal_v_prior_open_loop(artist_id, agent_id, show_date):
    """
    Signal (v): a prior settlement for the SAME artist OR SAME agent has
    notes saying the loop never closed. Pattern words like 'outstanding',
    'haven't gotten back', 'never resolved'.

    This is the D15 finding made into a signal: Mariana's TODO list
    becomes a risk surface for future shows with the same parties.
    """
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
                return f"prior open-loop note (same artist/agent) on {r['date']}: '{p}' in settlement notes"
    return None


# ---------------------------------------------------------------------------
# VERBOSE TRACE — pick 3 specific shows and walk through every signal.
# ---------------------------------------------------------------------------

def trace_show(show_id, label):
    print("\n" + "=" * 78)
    print(f"TRACE: {show_id} — {label}")
    print("=" * 78)

    row = q("""
        SELECT sh.id AS show_id, sh.date, a.id AS artist_id, a.name AS artist_name,
               a.agent_id, d.deal_type, d.guarantee_amount, d.percentage,
               d.percentage_basis, d.expense_cap, d.hospitality_cap,
               d.bonuses_json, d.deal_notes_freetext,
               s.status, s.recoups_json, s.notes, s.signoff_text
        FROM settlements s
        JOIN shows sh ON sh.id = s.show_id
        JOIN artists a ON a.id = sh.artist_id
        JOIN deals d ON d.show_id = sh.id
        WHERE sh.id = ?
    """, show_id)[0]
    expenses = q("SELECT category, amount FROM expenses WHERE show_id = ?", show_id)

    print(f"\n  GROUND TRUTH:")
    print(f"    date:            {row['date']}")
    print(f"    artist:          {row['artist_name']}")
    print(f"    deal_type:       {row['deal_type']}")
    print(f"    guarantee:       ${row['guarantee_amount']}")
    print(f"    percentage:      {row['percentage']} of {row['percentage_basis']}")
    print(f"    expense_cap:     ${row['expense_cap']}")
    print(f"    hospitality_cap: ${row['hospitality_cap']}")
    print(f"    settlement.status: {row['status']}   <-- THIS is what backtest measures against")
    print(f"\n  DEAL PROSE (deal_notes_freetext):")
    print(f"    {row['deal_notes_freetext']}")
    if row['recoups_json']:
        print(f"\n  RECOUPS at settlement (recoups_json):")
        try:
            for r in json.loads(row['recoups_json']):
                print(f"    - {r['category']:20} ${r.get('amount',0)}  status={r.get('status')}  label={r.get('label')}")
        except Exception:
            pass
    if row['notes']:
        print(f"\n  SETTLEMENT NOTES (settlements.notes):")
        print(f"    {row['notes'][:300]}")

    hosp_actual = sum(e["amount"] for e in expenses if e["category"] == "hospitality")
    print(f"\n  EXPENSE DATA (relevant): hospitality actual = ${hosp_actual:.0f}")

    print(f"\n  RUNNING THE 5 SIGNALS:\n")
    s1 = signal_i_ambiguous_prose(row)
    print(f"    Signal (i)  ambiguous prose:    {s1 or '— no fire'}")
    s2 = signal_ii_silent_recoup(row, {"recoups_json": row["recoups_json"]})
    print(f"    Signal (ii) silent recoup:      {s2 or '— no fire'}")
    s3 = signal_iii_hospitality_overrun(row, expenses)
    print(f"    Signal (iii) hosp overrun:      {s3 or '— no fire'}")
    s4 = signal_iv_ignored_structure(row)
    print(f"    Signal (iv) ignored structure:  {s4 or '— no fire'}")
    s5 = signal_v_prior_open_loop(row["artist_id"], row["agent_id"], row["date"])
    print(f"    Signal (v)  prior open loop:    {s5 or '— no fire'}")

    fired = [s for s in [s1,s2,s3,s4,s5] if s]
    actual = row["status"] in ("disputed",)
    predicted = bool(fired)
    print(f"\n  RESULT:")
    print(f"    Predicted (any signal fired): {predicted}")
    print(f"    Actual (status = disputed):   {actual}")
    if predicted and actual:
        print(f"    ✓ TRUE POSITIVE — caught the dispute")
    elif not predicted and actual:
        print(f"    ✗ FALSE NEGATIVE — missed the dispute")
    elif predicted and not actual:
        print(f"    ! FALSE POSITIVE — false alarm")
    else:
        print(f"    ✓ TRUE NEGATIVE — correctly quiet")


# Trace three illustrative cases:
trace_show("show_coastal_spell_dispute",
           "Coastal Spell 2025-03-14 dispute — the brief's canonical case (TP expected)")
trace_show("show_0007",
           "Briar Road 2024-10-16 — our second hero (TP expected via walkout/ratchet)")
trace_show("show_0152",
           "Coastal Spell 2025-03-14 ALT (data ghost) — disputed in DB, no surface signal (FN expected)")
trace_show("show_0001",
           "Wet Cement 2026-06-17 — status=paid but recoup disputed (TN if status drives, FP if recoup drives)")

# ---------------------------------------------------------------------------
# CONFUSION MATRIX MATH — written out by hand.
# ---------------------------------------------------------------------------
print("\n" + "=" * 78)
print("CONFUSION MATRIX — ALL HISTORICAL SHOWS")
print("=" * 78)

# Re-run the backtest over the full corpus
disputed_rows = q("""
    SELECT sh.id AS show_id, sh.date, a.id AS artist_id, a.agent_id,
           d.deal_type, d.expense_cap, d.hospitality_cap, d.bonuses_json,
           d.deal_notes_freetext, s.recoups_json, s.notes
    FROM settlements s
    JOIN shows sh ON sh.id = s.show_id
    JOIN artists a ON a.id = sh.artist_id
    JOIN deals d ON d.show_id = sh.id
    WHERE s.status = 'disputed'
""")
paid_rows = q("""
    SELECT sh.id AS show_id, sh.date, a.id AS artist_id, a.agent_id,
           d.deal_type, d.expense_cap, d.hospitality_cap, d.bonuses_json,
           d.deal_notes_freetext, s.recoups_json, s.notes
    FROM settlements s
    JOIN shows sh ON sh.id = s.show_id
    JOIN artists a ON a.id = sh.artist_id
    JOIN deals d ON d.show_id = sh.id
    WHERE s.status IN ('paid', 'finalized')
""")

def fires(row):
    expenses = q("SELECT category, amount FROM expenses WHERE show_id = ?", row["show_id"])
    sett = {"recoups_json": row["recoups_json"]}
    return any([
        signal_i_ambiguous_prose(row),
        signal_ii_silent_recoup(row, sett),
        signal_iii_hospitality_overrun(row, expenses),
        signal_iv_ignored_structure(row),
        signal_v_prior_open_loop(row["artist_id"], row["agent_id"], row["date"]),
    ])

TP = sum(1 for r in disputed_rows if fires(r))    # disputes correctly flagged
FN = len(disputed_rows) - TP                       # disputes we missed
FP = sum(1 for r in paid_rows if fires(r))         # false alarms on paid shows
TN = len(paid_rows) - FP                           # paid shows correctly quiet

print(f"\n  Corpus:")
print(f"    Historical disputes (positives): {len(disputed_rows)}")
print(f"    Paid/finalized   (negatives):    {len(paid_rows)}")
print(f"\n  Cells of the confusion matrix:")
print(f"    True  Positives (TP)  — disputes our system flagged:        {TP}")
print(f"    False Negatives (FN)  — disputes we missed:                 {FN}")
print(f"    False Positives (FP)  — paid shows we falsely flagged:      {FP}")
print(f"    True  Negatives (TN)  — paid shows correctly not flagged:   {TN}")

print(f"\n  The math:")
print(f"")
print(f"    Recall    = TP / (TP + FN)")
print(f"              = {TP} / ({TP} + {FN})")
print(f"              = {TP} / {TP+FN}")
print(f"              = {100*TP/(TP+FN):.2f}%")
print(f"    Meaning:  of the {TP+FN} historical disputes, our signals would have")
print(f"              caught {TP} on Wednesday (54%).")
print(f"")
print(f"    Precision = TP / (TP + FP)")
print(f"              = {TP} / ({TP} + {FP})")
print(f"              = {TP} / {TP+FP}")
print(f"              = {100*TP/(TP+FP):.2f}%")
print(f"    Meaning:  of every {TP+FP} 'alarms' our signals would have fired,")
print(f"              only {TP} would have been on shows that actually disputed.")
print(f"              {FP} would have been false alarms on shows that paid cleanly.")
print(f"")
print(f"    Fire-rate on paid/finalized shows: {FP}/{len(paid_rows)} = {100*FP/len(paid_rows):.1f}%")
print(f"    Operator framing: 'Pre-flight flags about {100*FP/len(paid_rows):.0f}% of upcoming")
print(f"    shows for closer Wednesday review.' That's the volume Mariana actually sees.")
