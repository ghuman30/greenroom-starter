# Scope

**Slice picked: 1 + 3** (deal capture & disambiguation + Wednesday pre-flight). The reasoning trail for *why* this pair vs. the other five candidates is in `slice-options.md`. This file is what I chose to build and what I chose to cut.

## In scope

**Slice spine — Deal Capture & Disambiguation (slice 1):**
- LLM extraction from `deals.deal_notes_freetext` → structured deal object (guarantee, percentage + basis, expense cap, hospitality cap, bonuses, **ratchets, walkout pots, gross-threshold bonuses, recoup line items**)
  - Anchor: 64% of vs-deals carry prose-only structure (D5). Freetext is never null (0/537); structured columns are 29–76% null (D5).
- Ambiguity score per clause. LLM flags clauses that admit multiple readings (e.g., "marketing recoup against gross" — inside or outside the cap)
  - Anchor: 94 surprise recoup line items in settlement that aren't mentioned in prose (D2). The dispute thread is 80 words and three of them are ambiguous (`dispute-thread.md:66`).
- Side-by-side: prose with clause-level highlights ↔ structured deal. Mariana can edit the structured form.
- Shareable agent-confirmation link: agent sees the same artifact, confirms or flags ambiguity *before show* (the ii.5 model).
- Versioned: amendments tracked.

**Slice surface — Wednesday Pre-Flight (slice 3, thin):**
A single screen listing upcoming shows with concrete, ranked risk flags. Each flag is action-oriented (what to do *now*).
- Flag (i): clause-level ambiguity surfaced by the LLM
- Flag (ii): silent-on-recoup deals where the agent/agency historical pattern says a recoup is likely. Anchored to D2 + D3.
- Flag (iii): hospitality trending over cap (actual expenses Wednesday vs. `hospitality_cap`). Anchored to D7.
- Flag (iv): structural complexity not yet represented (ratchets, walkouts). "Settlement math will need manual work — confirm with agent."

**Eval set (mandatory for an Applied AI PM case):**
- 10–15 hand-labeled deal-notes-freetext entries with expected extraction + ambiguity labels.
- Precision / recall reported on extraction.
- A separate eval on ambiguity classification (small set of known-ambiguous vs known-clean clauses).

---

## Refinements after design audit (branch 3.7, Arshdeep-raised)

### HITL state machine — load-bearing
- `prose_entered → extracted_draft → mariana_confirmed → agent_pending_review → agent_confirmed`
- Until `mariana_confirmed`, downstream consumers see "pending booker review," not the extracted values
- Agent confirmation surface is plain-English restatement of email + per-field source quotes + ambiguity flags as two-reading questions with $ delta — NOT JSON

### Amendment versioning — new schema
- `deal_versions` table tracks every change; default behavior is agent re-confirmation required
- Open product question: every-amendment vs material-only — flagged in assumptions.md

### Structured fields: auto-populated, not mandatory
- Mandatory fields produce garbage. LLM-populated + Mariana-confirmed produces structure without coercion.
- The structured field becomes a byproduct of confirmation, not a separate data-entry burden.

### Signal corrections after Q10 audit, then Q13 stress-test
- Replaced backtest signal (ii) (retrospective) with signal (ii.pred) using artist+agent+agency history → genuinely Wednesday-knowable
- Marked signal (iii) hospitality_overrun as "audit-only" given seed timing artifacts (D25, D26); replaced with signal (iii.pred) using prior-history rate
- Added signal (vi): "deal not agent-confirmed" — reads new schema (`deals.agentConfirmedAt`)
- Added signal (vii) **agent severity modifier** from `agents.preferences_notes` — scales severity ±1 step based on agent posture ("pushes back" → +1; "easygoing" → -1)
- Added signal (ix) **new-to-venue agent badge** (informational, doesn't fire as a risk on its own)
- **Dropped signal (viii) marketing-expense heuristic** after Q13 stress-test: 65% fire-rate on paid shows, precision 4.9% ≈ base rate, lift 1.0x. Inflating recall with noise = dishonest
- **Final Wednesday-honest baseline: 41.7% recall** on 24 historical disputes (10/24), 8.1% precision, 23.6% fire-rate on paid shows — see `notes/queries/q11_backtest_corrected.py`

### Build-affecting schema additions
- `deals.extracted_deal_json` — full LLM output incl. walkouts/ratchets/planned recoups/ambiguity flags
- `deals.agent_confirmed_at`, `deals.confirmed_by`
- `deal_versions` table for amendment tracking
- `settlements.calculation_json` populated by our path (was 537/537 NULL per D11)

---

## Out of scope (deferred — "we'd ship next, ran out of time")

- **Settlement statement (slice 5).** Sarah's three asks include a traceable statement. Real follow-on once the structured deal is live. Memo will say: "this is the natural next slice."
- **2am settlement walkthrough surface (slice 4).** Once the deal is unambiguous, the 2am UI becomes mostly mechanical. Defer.
- **Mobile TM view.** The agent-confirmation link should be mobile-readable from day one. Pre-built UX work for Diego's specific phone moment is deferred (ii.5 stance).
- **Comp-policy reconciliation.** `comps.counts_toward_gross` is one of the brief's noted realism seams. Mention in the memo as a candidate for the next slice.

---

## Explicitly cut (and why — the defensible cuts)

- **A Vs-deal calculator.** This is the obvious slice the case writers explicitly warn against. Pri's memo diagnoses the company's whole problem as "comprehensive but mediocre" (`ceo-memo.md:21`); building more deal types is more comprehensive, not more crafty. Also: the math isn't where the trust is built (D1 — disputes open the next morning, after the math has already been "signed"). Cutting this with confidence.
- **Dispute-resolution workflow (slice 6).** Lagging indicator. The case writers want upstream leverage; building UI for *after* a dispute opens is exactly the wrong direction.
- **Audit trail / 2am paper trail (slice 2).** A meeting-notes feature. Doesn't address the root cause. If sign-off text is already theatre (D1), more capture of theatre is more theatre.
- **Auto-creation or auto-acceptance.** The agent confirmation must be an *active* step. Auto-confirm would re-introduce the "deal is a ghost" problem. We're optimizing for *forcing* the explicit confirmation moment, not removing it.
