# Evidence Log

Every claim in the memo traces back to a finding here. Each finding has a file path + line number for transcripts/data files, or a query script for DB-derived facts. No paraphrasing of stakeholder quotes.

**The six findings spotlighted in the memo's "Reading past the badge" section:**

| Memo row | Finding | This file |
|---|---|---|
| 1 | Briar Road's amendment-in-prose self-flag | D9 |
| 2 | Two "signed" concepts that disagree | D1 + D10 |
| 3 | Coastal Spell carries the resolved $12,285 but status says disputed | D6 + D8 |
| 4 | `/reports` hides 29 future-dated settlements + 2 in-flight disputes | D18 + D20 |
| 5 | 94 silent recoups; word "recoup" appears in 1 of 537 deal notes | D2 + D22 |
| 6 | `agents.preferences_notes` is dense relationship intelligence the product ignores | D29 + D33 + D34 |

**Conventions used below:**
- **D-numbers** are sequential as the findings were discovered. Where a later finding supersedes an earlier number (e.g., recall numbers), the older row is annotated.
- **Where Arshdeep flagged a miss** (caught something I'd missed during the build), it's noted inline so the reviewer can see the iteration.

---

## CEO frame: completeness vs. craft, settlement is the Q1 craft bet

> "We are winning on completeness and losing on craft."
— `data/ceo-memo.md:21`

> "Eighteen percent of our customer base actively uses the in-app settlement tool. The other 82% — including most of our largest accounts — default to spreadsheets."
— `data/ceo-memo.md:29`

> "For Q1, I want our craft bet to be **settlement.** Two reasons. One: it's the most trust-critical moment in the relationship between our customers and their customers' customers. Two: 82% of our base is going around our product to do this. That's not a feature gap. That's an existential signal."
— `data/ceo-memo.md:37`

---

## The deal-as-a-ghost pattern (multi-persona convergence)

> "I want fewer surprises in that 2am conversation. Most of the friction comes from things that were knowable on Wednesday — the hospitality bill is going to run over the rider cap, or the marketing line we agreed to doesn't have a clear deduction order, or the deal email from the agent has a sentence that could mean two different things. If I knew those things on Wednesday I'd email the agent then. The Friday-night version of that conversation goes much worse than the Wednesday-afternoon version."
— Mariana, `data/transcripts/mariana.md:59`

> "I keep saying we need to do something about how we capture deal terms — Andrea's email last December was 80 words long and four of them were ambiguous and there's no version of the truth in our system. It's just in her head and ours."
— Mariana, `data/transcripts/mariana.md:112` (from dispute thread postscript)

> "I wish she could see, before a show even happens, whether the deal we agreed to is going to be a clean one or a messy one. Right now we find out at 2am. By then it's too late to fix anything. If we could see Wednesday 'this deal is going to have an ambiguous expense fight' we could resolve it cold, in writing, with the agent. The way settlement works now is we're paying a tax on every poorly-written deal email we ever signed."
— Marcus, `data/transcripts/marcus.md:55`

> "The thing that bothered me about that one wasn't even the money. It was that there was no canonical version of what the deal was. Mariana had her notes, I had my email, Andrea had her recollection of the negotiation, and none of them perfectly agreed. The deal was a ghost."
— Sarah Kim (WME), `data/transcripts/sarah-kim.md:29`

> "A version of the deal we both agreed on, in one place, that had unambiguous terms. The deal email needed three more sentences to be unambiguous. They never got written because deal emails get written at 11pm by overworked agents. So the ambiguity gets pushed downstream into settlement, where it costs everyone more time."
— Sarah Kim, `data/transcripts/sarah-kim.md:33`

> "One: ambiguous deal terms. The deal email from the agent has some sentence that means different things to me and the venue, and we have to figure out which read we're going with at the table. That should never happen at the table — that should have been resolved when the deal was negotiated."
— Diego (TM), `data/transcripts/diego.md:21`

---

## Showing the math / provenance

> "Right now if I run a settlement in the in-app tool I have no real visibility into how it got to the answer. The spreadsheet I built has every line called out — I can show the tour manager exactly where each number came from."
— Mariana, `data/transcripts/mariana.md:37`

> "The booker's math is opaque. They give me a number and I have no idea how they got there. If I have to ask 'where did the $14,427 come from' and they have to explain it for ten minutes from memory, I'm not signing that. I want to see the math."
— Diego, `data/transcripts/diego.md:25`

> "Itemization. Provenance. Tone. ... Provenance: I want to be able to trace each line to a source. The CC fees should match the POS. The expenses should tie to actual receipts I could ask for."
— Sarah Kim, `data/transcripts/sarah-kim.md:45`

---

## Wednesday pre-settle / expense aggregation

> "Pulling expenses together. The CC fees are in Greenroom. The bar charges are in the POS. The hospitality is in receipts that the production manager throws on my desk. ... If you could just have all the expenses ready when I sat down to settle, that alone would change my life."
— Mariana, `data/transcripts/mariana.md:67`

---

## Audit trail / 2am paper trail

> "I want a paper trail. Right now there's literally no record of what happened in the room when we settled. The tour manager points at hospitality, I explain, we agree. That conversation isn't in any system."
— Mariana, `data/transcripts/mariana.md:61`

---

## Agent pre-review

> "Being able to look at the math before I sit down. ... If I could pre-review and we could just discuss the line items I'm confused about, the conversation would be 10 minutes instead of 45."
— Diego, `data/transcripts/diego.md:43`

> "If I could see the settlement before my tour manager signed off on it — like, get a preview while they're at the table — I'd be a faster signoff and there'd be fewer next-day disputes."
— Sarah Kim, `data/transcripts/sarah-kim.md:55`

---

## Business cost (Marcus)

> "When I think about the cost of a bad settlement, the dollars on the night are the smallest part. The bigger thing is whether we lose the relationship."
— Marcus, `data/transcripts/marcus.md:31`

> "Three years ago there was an indie agent — I won't name them — who had a bad settlement experience here. ... I called the agent and asked. She told me, very nicely, that she'd been routing through The Basement for those tours instead. That was about $80K in gross revenue we lost over a year."
— Marcus, `data/transcripts/marcus.md:29`

> "Right now we collectively spend probably 25 hours a month on settlement and post-settlement cleanup. If that were five hours a month, that's 20 hours of senior labor back into booking, marketing, and sponsor work — which are the levers that grow revenue."
— Marcus, `data/transcripts/marcus.md:41`

---

## The Coastal Spell dispute — the canonical failure case

> "Our deal was $5,000 vs 80% of net after expenses, expenses capped at $2,500. ... The difference looks like the marketing recoup ($900). Was that supposed to come off the gross before we calculated net, or is it part of the expenses bucket capped at $2,500?"
— Daniel Hwang (WME), `data/dispute-thread.md:17–21`

> "The deal email from Andrea last December said 'expenses capped at $2,500, marketing recoup of $900 against gross.' I read that as the recoup being a separate deduction off gross, before we apply the 80%."
— Mariana, `data/dispute-thread.md:40`

> "Honestly, I think it can be read either way. 'Expenses capped at $2,500, marketing recoup of $900 against gross' is ambiguous."
— Daniel Hwang, `data/dispute-thread.md:66`

> "I want to flag this is the third time we've had a marketing recoup interpretation issue this year, all with WME."
— Mariana, `data/dispute-thread.md:86`

> "I'll send the additional $720 today. We're going to settle on Andrea's read this time but I want to flag for the record that we don't think it was the only fair reading of the deal."
— Marcus, `data/dispute-thread.md:100`

---

## The Vs-deal calculator gap (quant evidence to cite carefully)

Three numbers in the corpus that are easy to confuse:
- Brief: "About 62% of deals at The Crescent fall outside what the tool can settle." — `Settlement at The Crescent` Notion brief.
- Mariana: "Probably 70% of my deals at this venue are vs deals." — `data/transcripts/mariana.md:33`
- CEO: 82% of *Greenroom's customer base* uses spreadsheets, not the tool. — `data/ceo-memo.md:29`

These are three different denominators (deals-at-Crescent-outside-tool, vs-share-at-Crescent, customer-base-bypassing-tool). Always cite the right one.

---

## Embedded messiness called out by the case

From the Notion brief (provided in chat):

> "Disputed status with positive sign-off | UI shows 'Disputed', artist/agent sign-off text says 'Looks good — TM' | Reads past the badge to the data and designs a solution that prevents such messiness"

— Reminder: status fields and prose can disagree. The case explicitly rewards candidates who spot this.

From the README:

> "The deal `notes_freetext` field is the truth. The structured fields (`guarantee_amount`, `percentage`, `bonuses_json`, `expense_cap`) are filled inconsistently. Mariana enters deals as prose because the structured fields don't model the actual deals well. This mismatch is part of the realism."
— `README.md:116`

---

# DB findings (D = data-supported, with reproducible SQL)

Queries in `notes/queries/q0{1,2,3,4}.py`. The DB at `data/greenroom.db` is the source.

## D1. The in-room sign-off is theatre. 85% of disputes open the next morning.

Of 26 settlements with `disputed_at`:
- **In-room (< 4h after sign-off): 3**
- **Next morning (4–36h): 22**
- Later (>36h): 1

Sign-off text doesn't carry the dispute signal — the distributions of phrases on **disputed** vs **paid** settlements are nearly identical:

| Phrase | Disputed count | Paid count |
|---|---|---|
| `'👍'` | 7 | 74 |
| `'OK. Good night.'` | 6 | 109 |
| `'ok wire monday'` | 4 | 79 |
| `'Looks good.'` | 3 | 90 |
| `'Sign off.'` | 2 | 95 |

**Interpretation.** The TM and agent sign off in the room with a standard phrase regardless of how the show will be received the next morning. The actual dispute discovery happens when the agent reads the statement. This empirically validates the brief's planted seam ("Disputed badge with positive sign-off") as a *systemic* pattern, not a one-off.

(Query: `notes/queries/q03_deeper.py` (a), `q04_timing.py` (a))

## D2. "Surprise recoup" is the dominant dispute mechanism. 94 line items, marketing dominates.

Recoup line items that appear in `settlements.recoups_json` but are not mentioned in `deals.deal_notes_freetext`:

| Category | Surprise count | Disputed |
|---|---|---|
| `marketing` | 56 | (in 20 settlements total) |
| `production_overage` | 22 | |
| `prior_advance` | 10 | |
| `hospitality_overage` | 6 | |

**Interpretation.** The Coastal Spell dispute (`data/dispute-thread.md`) is not a one-off — it's the canonical instance of a system-wide pattern. Recoups are being added at settlement that were not negotiated in the deal email. Marketing-recoup is the largest single category. (Query: `notes/queries/q04_timing.py` (c))

## D3. WME is *not* Mariana's highest-risk agency. Wasserman is. Paradigm carries the most complex deals.

| Agency | Shows | `disputed` status | All dispute episodes | Rate |
|---|---|---|---|---|
| Wasserman | 102 | 8 | 17 | **16.7%** |
| Paradigm | 55 | 4 | 6 | 10.9% |
| Independent | 291 | 9 | 30 | 10.3% |
| CAA | 48 | 2 | 3 | 6.2% |
| WME | 41 | 1 | 2 | **4.9%** |

Complex-prose vs-deals (containing "ratchet/walkout/escalator/tier/sliding") by agency:

| Agency | Vs-deals | Complex prose | Rate |
|---|---|---|---|
| Paradigm | 25 | 14 | **56%** |
| Wasserman | 62 | 20 | 32% |
| CAA | 22 | 6 | 27% |
| Independent | 64 | 15 | 23% |
| WME | 22 | 4 | 18% |

**Interpretation.** Mariana's mental model ("third time this year, all WME" — `dispute-thread.md:86`) is wrong on the agency. WME has the cleanest base rate. The dispute pattern is *salient* with WME because each one is high-stakes (one big agent, name attached, the Coastal Spell case). The *frequency* problem is Wasserman + Paradigm. A pre-flight surface grounded in data corrects this perception. (Query: `q04_timing.py` (b), (d))

## D4. Vs deals dispute at ~1.7x flat-deal rate. The math complexity matters.

| Deal type | Shows | Disputed status | All episodes | Rate |
|---|---|---|---|---|
| `vs` | 195 | 14 | 29 | **14.9%** |
| `percentage_of_net` | 109 | 6 | 10 | 9.2% |
| `flat` | 185 | 3 | 16 | 8.6% |
| `door` | 30 | 1 | 3 | 10.0% |
| `percentage_of_gross` | 18 | 0 | 0 | 0.0% |

Deal-type mix at The Crescent:
- Vs: 36.3% (Mariana's stated "70%" is wrong on detail; the spirit is "62% are vs-flavored not handled by the in-app tool" — Vs + % of net + Door = 62.2%, which matches the brief.)
- Flat: 34.5%
- % of net: 20.3%
- Door: 5.6%
- % of gross: 3.4%

(Query: `q01_shape.py`, `q04_timing.py` (b.2))

## D5. Deal-prose structure that the schema cannot represent. 64% of vs-deals.

Patterns inside vs-deal `deal_notes_freetext` that the structured columns can't carry:

| Pattern | Matched vs-deals | % |
|---|---|---|
| `gross_threshold_bonus` ("if gross > $X" / "if attendance > N") | 48/195 | 25% |
| `walkout_pot` ("100% of gross above $X") | 32/195 | 16% |
| `tier_ratchet` ("ratchets to 95% over 80%") | 27/195 | 14% |
| `vs_gross_variant` ("vs 90% of gross, no expenses") | 17/195 | 9% |

`deal_notes_freetext` is **never NULL** (0/537). Structured fields are NULL **29–76%** of the time. 9 of 20 sampled vs-deals (45%) had numerical values in prose that were absent from the structured columns.

**Interpretation.** The schema is the wrong shape. The freetext is the source of truth. This is the empirical basis for an LLM-extraction approach: we're not replacing data, we're *promoting* the prose to a structured form the system can reason over. (Query: `q01_shape.py`, `q02_seams.py` (d), `q03_deeper.py` (e))

## D6. The Coastal Spell show's data is itself drifted.

`show_id = show_coastal_spell_dispute`, date 2025-03-14, status `disputed`, `total_to_artist = $12,285` — but $12,285 is the **agreed post-dispute amount** ($11,565 was the originally calculated number per `data/dispute-thread.md`). `signoff_text = "OK — but flag any future marketing recoup deals."` and `notes` carries a full prose backstory ("Marcus authorized additional $720 to resolve, but the formal revision hasn't been pushed back into the system yet").

**Interpretation.** Even the cleanest hero case in the corpus carries state drift — status hasn't moved from `disputed` to `revised`/`finalized` even though the money has been agreed. The state machine and the operational reality have diverged. Worth showing in the memo as an example of the broader problem the tool isn't capturing what actually happened. (Query: `q02_seams.py` (b), `q03_deeper.py` (b))

## D7. Hospitality cap overruns are Wednesday-knowable.

334 shows have a `hospitality_cap`:
- 30% exceeded the cap (101)
- 25% exceeded by >10% (85)
- 16% exceeded by >25% (53)

Worst sampled: $200 cap → $513 actual (2.56x).

**Interpretation.** This is exactly the kind of "knowable on Wednesday" signal Mariana described (`mariana.md:59`). The expense rows are already entered. The pre-flight surface can read them. No prediction needed — pattern-detection on existing data. (Query: `q03_deeper.py` (d))

---

# Skepticism pass — findings from adversarial pass (D8–D17)

## D8. Status drift is bidirectional.

The brief explicitly planted "disputed badge with positive sign-off" (Coastal Spell). The data shows the *reverse* drift is also real:

- **Wet Cement 2026-06-17** (`show_0001`): status=`paid`, but `recoups_json[0]` has a $340 marketing recoup with status=`disputed`. Settlement notes: *"TM emailed two weeks later flagging the IG boost recoup — never resolved, never re-issued. Carrying as outstanding."* So the parent settlement says paid; a child line item says disputed; the prose admits the relationship is unresolved.
- Cross-table: 22 shows have `shows.status='settled'` but `settlements.status='disputed'`. 8 have `shows.status='settled'` but `settlements.status` is mid-flight (draft, submitted, in-review). 9 have `shows.status='booked'` but a fully signed/paid settlement — the show.status was never advanced after the show happened.

(Query: `q05_skeptical.py` (f), `q06_followups.py` (c))

## D9. Briar Road is a second hero case — arguably better than Coastal Spell for the memo.

`show_0007`, Briar Road, 2024-10-16. Deal type: vs.

**Deal note (verbatim, with the planted operational note inside):**
> "$2,631 vs 90% net + walkout pot. After breakeven on guarantee + expenses, all incremental gross goes to artist. Hospitality cap $400. +$400 if gross > $11,000; Walkout pot: 100% of gross above $3,200. **[Updated 4 days before show via phone call with agent: bonus threshold dropped to $6,000. Note: structured field still reflects original $11,000 — confirm before settlement.]**"

Settlement notes:
> "[Mariana, internal] TM signed off Sunday morning. His assistant emailed Monday questioning the production-overage line — that's why this is showing as disputed. Need to either re-send a clean version or close the dispute. Haven't gotten back to it."

Why this is more powerful than Coastal Spell as a memo anchor:
- It's a planted seam *inside the freetext itself* — Mariana literally wrote "the structured field is wrong" in the prose, because the product has no amendment mechanism.
- It's not a marketing recoup — it's a **production overage**. Disproves the over-narrow read that the slice is "fix marketing recoups."
- The disputing party is not the TM but the TM's *assistant*. Asymmetric dispute roles: the signing party in the room and the questioning party the next day can be different humans.
- The notes capture the operational debt: *"Haven't gotten back to it."* The settlement notes field is being used as Mariana's TODO list.

This is the second canonical case. We will use it in the memo. (Query: `q06_followups.py` (b))

## D10. The state machine has two concepts of "signed" and they disagree.

- 23/24 disputed shows have `signed_at = NULL` but `signoff_text` populated.
- 1/24 went through formal signed state before disputing.
- All 24 went `submitted → in_review → disputed`, skipping `signed`.

Re-running the dispute-lag with submitted_at as the anchor: 22/24 disputes opened **12–36 hours after submission** (i.e., next morning). 2 later. Zero in the first 12 hours.

**Interpretation.** The system actually models the state machine *correctly* — `signed_at` only fills when an agent reads without disputing. But the UI captures `signoff_text` from the room before that, which presents as "signed" colloquially. The TM's "OK" is a textual artifact, not a state transition. The product has the right plumbing but doesn't separate the two concepts, so operators read "looks good — TM" as "signed" and trust drifts.

(Query: `q05_skeptical.py` (e), `q06_followups.py` (f), (h))

## D11. `calculation_json` is universally NULL (537/537).

The settlements table has a column to store the reasoning trail. It's used **zero** times. The current product computes math at render time and never persists it.

**Interpretation for slice.** When we build, we MUST populate `calculation_json`. That's how we deliver Mariana's ask (`mariana.md:37`: *"every line called out — I can show the tour manager exactly where each number came from"*). Infrastructure exists; usage doesn't. (Query: `q05_skeptical.py` (n))

## D12. Tier ratchets are populated in `bonuses_json` but invisible to the engine.

27 vs-deals have tier_ratchet entries in **both** freetext and bonuses_json. 4 have them only in bonuses_json. 0 have them only in freetext. So the structured field is actually well-populated when the prose mentions a ratchet.

But `lib/dealMath.ts:243` returns `"Tier ratchets need vs-deal or % of net support — not yet handled"` for every single one. The data captures the structure; the engine ignores it.

**Interpretation.** The system is *worse than it looks*. It's not just "vs deals aren't supported" — it's "even when the booker correctly enters the structured bonus, the engine throws it away." A pre-flight surface should flag this for Mariana: "this deal has a tier ratchet you've encoded; the in-app tool will ignore it." (Query: `q06_followups.py` (e), `dealMath.ts:243`)

## D13. Hospitality is the *only* expense category that gets absorbed by the venue.

| Category | Rows | Absorbed | $ absorbed | $ total | % absorbed |
|---|---|---|---|---|---|
| hospitality | 605 | 68 | $5,894 | $184,220 | 11.2% |
| (every other category) | … | **0** | **$0** | … | **0.0%** |

**Interpretation.** Sound, lights, production, marketing, security, backline — never absorbed. Only hospitality. This is the venue's operational behavior of preserving artist relationships at financial cost (Mariana: *"the whiskey ran over but I'm absorbing the difference"* — `mariana.md:41`). It's also a Wednesday-knowable signal: if hospitality is trending high, history says Mariana will eat the overage — and the agent will never know. The product could surface that subsidy. (Query: `q05_skeptical.py` (m))

## D14. Promo comps have inconsistent `counts_toward_gross` treatment.

Of 141 promo comp rows: **37 yes, 104 no**. Every other category is consistent (artist_gl always 0, label always 0, etc.). Only `promo` is the mixed category.

**Interpretation.** Mariana described this exactly: *"the rules vary by deal."* The 37 yes-cases are presumably radio-giveaway or 2-for-1 ticket promotions where the artist's deal counted those as paid. Surface this in pre-flight when the deal language is silent on promo comps. (Query: `q05_skeptical.py` (o))

## D15. `settlements.notes` is being used as an operational to-do list.

Three documented "TODO" entries embedded in the notes field:
- Coastal Spell: *"Marcus authorized additional $720 to resolve, but the formal revision hasn't been pushed back into the system yet."*
- Briar Road: *"Need to either re-send a clean version or close the dispute. Haven't gotten back to it."*
- Wet Cement: *"Carrying as outstanding."*

These are open loops Mariana has visibility into only because she wrote them. There's no system surface that lists open loops. A Wednesday pre-flight could parse `settlements.notes` for follow-up flags and surface them. (Query: `q05_skeptical.py` (h))

## D16. The boilerplate "Comp tickets: 12. Revenue impact accepted." is decoupled from reality.

8 settlements carry that exact string. Actual comp counts on those shows: **9, 32, 26, 28, 48, 22, 28, 15**. The "12" in the boilerplate doesn't correspond to any of them.

**Interpretation.** The booker is copy-pasting a stock phrase to *dispose* of a comp-related exception without re-evaluating. Cold Comfort 2025-07-24 had 48 comps (against 517 sold — ~9% of paid attendance). The relationship cost might be real; the audit trail is fictional. This is the prose-vs-reality drift the case warned us about, at full force. (Query: `q06_followups.py` (a))

## D17. There's a second 2025-03-14 Coastal Spell show (`show_0152`) — a "data ghost."

Same artist, same date as the dispute thread's canonical show. *Different* deal: "$4,988 vs 90% gross — no expenses come out." Status: `disputed`. Signoff: `'Looks good.'` No settlement notes. No recoups. No `signed_at`. Timestamps are properly sequenced (drafted → submitted → review → disputed).

**Interpretation.** The data SAYS something happened (a dispute was opened) but the surrounding context is silent (no notes, no recoups, no resolution). This is the case writers' purest expression of "what the UI shows you isn't what the data says — and neither is necessarily what actually happened." We may or may not solve this in the slice, but we should call it out in the memo as evidence we read past the canonical example. (Query: `q06_followups.py` (d))

---

# App-vs-DB audit (D18–D21) — the dashboard is filtering operational reality out

Mechanism: `lib/queries.ts:41,128` filters all aggregates to `shows.date <= today`. With today = 2026-05-22, **29 of 537 shows are hidden from every aggregate the operator sees.**

## D18. The app hides 29 future-dated settlements — including 2 incoming disputes.

> 🔍 **Arshdeep flagged this.** While inspecting the running app he noticed `/reports` shows "22 disputed past settlements" but my evidence file claimed 24. The 2-vs-24 gap turned out to be `lib/queries.ts:41` filtering `shows.date <= today` on every aggregate — hiding 29 future-dated settlements including 2 in-flight disputes (D20). This is the finding that justifies why `/preflight` reads the un-filtered DB instead of using the existing helpers.

| Status | App count | DB count | Hidden |
|---|---|---|---|
| draft | 1 | 1 | 0 |
| submitted | 3 | 8 | 5 |
| in_review | 3 | 7 | 4 |
| signed | 5 | 12 | 7 |
| disputed | **22** | **24** | **2** |
| revised | 1 | 2 | 1 |
| finalized | 29 | 32 | 3 |
| paid | 440 | 447 | 7 |
| voided | 4 | 4 | 0 |

The **2 hidden disputes** are not hypothetical — they have populated `disputed_at` timestamps:

1. **House of Lights, 2026-06-10** (Independent agency, agent: Pat Cho). Flat deal. Signoff: `'👍'`. Settlement notes: *"Marketing recoup pre-deducted from gross."* — and a marketing recoup on a flat deal is itself an oddity (flat means flat).
2. **Sunday Drivers, 2026-07-01** (Paradigm agency, agent: Kev Park). Vs deal. Signoff: `'OK. Good night.'` Paradigm has the highest complex-prose rate of any agency (56% of vs-deals, per D3). This dispute fits the pattern; the operator cannot see it coming.

Plus a **revised** future-dated case the operator also can't see:
3. **Low Rooms, 2026-05-29** (Independent, agent: Cass Burke). Vs deal, status `revised`.

**Interpretation.** The dashboard is filtering operational reality out. The operator's job at 2pm Wednesday is to know what's heading toward a 2am argument; the dashboard hides exactly the shows where that argument is in motion. This is the case in microcosm — and it's the direct justification for our slice 3 (Wednesday pre-flight) reading from the un-filtered view, not the dashboard's. (Query: `q08_app_vs_db.py` (b), (c), (g))

## D19. Show.status is stale for past shows too.

| Bucket | shows.status | Count |
|---|---|---|
| past (date ≤ today) | settled | 502 |
| past | **booked** (stale) | **5** |
| past | **advanced** (stale) | **1** |
| future | booked | 15 |
| future | advanced | 14 |

6 past shows still carry `shows.status` of `booked` or `advanced` — they happened, they settled, but the show-level status was never updated. Parallel to D8 (settlement-level status drift). (Query: `q08_app_vs_db.py` (f))

## D20. Hidden future dispute activity is concentrated where D3 said it would be.

The three hidden disputes/revisions by agency:

| Agency | Agent | Artist | Date | Status |
|---|---|---|---|---|
| Independent | Cass Burke | Low Rooms | 2026-05-29 | revised |
| Independent | Pat Cho | House of Lights | 2026-06-10 | disputed |
| Paradigm | Kev Park | Sunday Drivers | 2026-07-01 | disputed |

Paradigm has 56% complex-prose vs-deals (highest of any agency, D3). It tracks perfectly that Paradigm's incoming dispute is on a vs deal. The operator's dashboard says zero Paradigm disputes are in progress; the DB says one is. (Query: `q08_app_vs_db.py` (h))

## D21. Top-level metrics are systematically distorted.

| Metric | App shows | DB truth |
|---|---|---|
| Disputed rate | 22/508 = 4.3% | 24/537 = 4.5% |
| Unsupported deal types | 63% | 62% |
| Total paid to artists | $1,943,924 | $2,035,260 |
| Settlements with recoups | 79 | 84 |

The deltas are small individually but cumulative — **$91,336 of artist payments are invisible** to anyone reading the dashboard. The dashboard is not just incomplete; it is *systematically* a small percent off in the direction of "less activity than is actually happening." (Query: `q08_app_vs_db.py` (e))

## How this changes the build

- **Our Wednesday pre-flight must read from the un-filtered DB**, not through `getReports()`. If we use the existing helpers naively, we re-implement the bug. Build note: write our own query layer for the pre-flight signals.
- **The slice's memo headline gets stronger.** We can claim, with citations: "the dashboard hides the operational risk it's supposed to surface. Our pre-flight is built to read the truth." That's a 1-sentence pitch.
- **Hidden disputes are pre-flight test cases.** Sunday Drivers 2026-07-01 (Paradigm vs deal, hidden disputed) and House of Lights 2026-06-10 (Independent flat with mysterious marketing recoup) are perfect cases to demonstrate the pre-flight catching what the dashboard doesn't.

### Reframing after browser verification (Arshdeep pushed on accuracy)

Confirmed in the running app at `http://localhost:3000`:
- `/reports` actually says *"22 of 509 **past** settlements ended in some form of dispute"* — the "past" qualifier is explicit. The UI labels are correct, not misleading.
- `/shows` similarly bounded with relative date labels.
- The 2 future-dated "hidden" disputes exist in **impossible operational states** in the seed (a `disputed` settlement for a show that hasn't happened). In real production they wouldn't exist.

**Honest reframe for the memo:** the dashboard surfaces past settlement risk *correctly within its scope*. It has no forward-looking surface for upcoming shows. **That's a missing capability, not a bug.** Our pre-flight is the new capability that fills that gap. We do NOT touch /reports or /shows — we ADD a separate surface. Cleaner pitch, more defensible in the interview.

The seed-data anomalies (future shows in non-draft settlement states) are themselves a small finding worth a one-line note in the memo: "even the seed corpus has impossible states that wouldn't exist operationally — another expression of the data-drift theme."

---

# Build-prep + offline backtest (D22–D24)

## D22. The deal-notes corpus is *terse* and uses a small vocabulary.

- 100% of deals have `deal_notes_freetext` populated (D5 already showed this).
- Length: min 21 chars, median **62 chars**, p75 90, max 375. **Most deals are 1–3 short sentences.**
- Common terms (% of 537 deals): `guarantee/g'tee` 58%, `net` 45%, `expense cap` 43%, `vs` 34%, `hospitality` 34%, `gross` 15%.
- **Notable absences:** `marketing` appears in **1/537** (0.2%); `recoup` appears in **1/537**. Yet 56 settlements carry marketing recoup line items (D2). So recoups in deals are almost always *implicit* — the deal email doesn't use the word; the recoup appears at settlement.
- Amendment language (`updated/amended/renegotiated/confirm before`) appears in only **3/537** — yet Briar Road (D9) and Coastal Spell aftermath (D6) both have amendments. Amendments are rarely structurally written in.

**Build implication.** The LLM extractor needs to handle terse abbreviated prose. The Q07a vocabulary list seeds few-shot extraction examples. The almost-total absence of the word "recoup" means the extractor must *infer* recoup possibility from contextual cues (agent history, deal structure), not just keyword matching.

(Query: `q07_build_prep.py` (a))

## D23. Eval set of 11 candidate shows — written to `notes/eval_set_candidates.json`.

Coverage:
- **Hero cases:** Coastal Spell (canonical), Briar Road (D9 second hero), Wet Cement (D8 paid-but-disputed-recoup)
- **Both hidden future disputes** as demo cases: Sunday Drivers 2026-07-01 (Paradigm vs with ignored tier_ratchet) + House of Lights 2026-06-10 (Independent flat with marketing recoup on a flat deal — itself a logic error)
- **Baselines:** clean flat, clean % of gross, door deal
- **Structural variety:** vs-net with tier_ratchet, vs-gross variant
- **Agency mix:** WME dispute (Mariner's Wake) for representative coverage

The JSON file is structured for hand-labeling: each entry has the freetext + structured fields, ready for the extraction eval.

(Query: `q07_build_prep.py` (b), output: `notes/eval_set_candidates.json`)

## D24. Offline backtest of pre-flight signals — heuristic recall = 54%, precision = 6.7%.

> ⚠ **SUPERSEDED by D27.1.** This 54% included signal (iii) hospitality_overrun as if Wednesday-honest, which Q10's seed-timing audit (D25/D26) later showed it isn't. The corrected Wednesday-honest baseline is **41.7%** (5 production signals; signal viii also dropped per D35). The memo uses 41.7%. Keeping this entry for traceability.

**Original framing (preserved for the record):**

Running the 5 candidate signals (heuristic baseline only — no LLM yet) against all 24 historically disputed shows:

| Signal | Catches | Coverage |
|---|---|---|
| (iv) Ignored structure (ratchet/walkout) | 6 of 24 | 25% |
| (i) Ambiguous prose (heuristic regex) | 4 of 24 | 17% |
| (ii) Silent recoup (surprise at settlement) | 4 of 24 | 17% |
| (iii) Hospitality overrun | 2 of 24 | 8% |
| (v) Prior open-loop notes | 1 of 24 | 4% |
| **ANY signal fires** | **13 of 24** | **54%** |

Same signals applied to the 479 paid/finalized shows fire on 182. So in confusion-matrix terms:
- **Recall:** 13 / 24 = **54.2%** (what fraction of historical disputes would we have caught)
- **Precision:** 13 / (13 + 182) = **6.7%** (of all our alarms, what fraction are real disputes)

**Recall miss analysis (the 11 disputes the heuristic missed):**
- Mostly vs and % of net deals where the dispute had no surface signal — these are deals where the *deal-type-itself* is the risk. We'd need a sixth signal "deal type unsupported + value > $X" but it would fire on every vs deal (1.7x dispute rate, not specific enough).
- The second Coastal Spell (`show_0152`, D17) — no recoup, no notes, no ambiguity signal. The "data ghost" by design.
- Sunday Drivers 2024-08-22 was a flat deal that disputed — flat deals dispute at 1.6%, so we'd need very subtle signals to catch.

**Reframing the 6.7% precision number.** Sounds bad, but the operator-facing framing is: "Flag 4–6 of ~12 upcoming shows for closer Wednesday review." That's a reasonable triage volume. The 38% fire rate on paid shows is the upper bound for an operator's "review queue" — not catastrophic.

**LLM upside — the build's eval target.** The (i) signal is heuristic regex today. A real LLM that semantically reads prose for ambiguity should materially push (i)'s recall higher. The eval set (D23) measures exactly this: same 11 cases evaluated against heuristic vs. LLM extraction. **Improvement on the (i) recall number is the build's named eval target.**

**Memo framing (honest, not over-claiming):**
> *"The heuristic baseline of our 5 pre-flight signals catches 54% of historical disputes — including both currently-hidden future disputes. The remaining 46% are mostly deal-type-level risk where the surface signal IS the deal type itself. Our LLM extractor lifts the (i) signal from regex to semantic; the eval set measures that lift. The build's named target is > 70% recall."*

Senior-PM thinking is *honest measurement with improvement plan*, not victory-lap numbers.

(Query: `q07_build_prep.py` (d), (d.2))

## Bonus finding from Q07(f). The engine math is correct for the deals it claims to handle.

0/203 mismatch between `dealMath.ts` output and stored `settlement.total_to_artist` for flat + % of gross deals. So the existing in-app engine is honest within its declared scope — it just declares too small a scope (the trap). This *removes* a memo angle ("the existing math is broken") and *strengthens* the slice cut: the engine isn't broken on what it claims to do; it's the *coverage* gap that drives spreadsheets.

(Query: `q07_build_prep.py` (f))

---

# Assumption audit (D25–D27) — Wednesday-knowability and corrected baseline

## D25. `expenses.entered_at` is a seed artifact. 99.8% concentrated on one timestamp.

| Distinct entered_at values | Rows |
|---|---|
| `2026-05-10 00:12 UTC` (seed run time) | **2,937** |
| `2025-03-14 00:00 UTC` (Coastal Spell day) | 5 |
| `2026-05-10 03:12 UTC` | 1 |
| Total | 2,943 |

**There are 3 distinct timestamps across all expense rows.** The seed doesn't model "when an expense became visible." Reinforces the Mariana quote: *"Pulling expenses together... half my Wednesday is just chasing down expenses"* (mariana.md:67) — there is no expense-knowability pipeline in the existing product, which is itself the operational gap.

(Query: `q10_audit_assumptions.py` (a))

## D26. 94% of expense rows are entered on or after the show date.

| Category | Total | Entered pre-show | % pre-show |
|---|---|---|---|
| hospitality | 605 | 39 | 6% |
| sound | 538 | 35 | 7% |
| production | 537 | 35 | 7% |
| lights | 537 | 35 | 7% |
| marketing | 354 | 22 | 6% |
| backline | 226 | 10 | 4% |
| security | 146 | 8 | 5% |

Combined with D25, this means: any backtest signal that relies on expense data is implicitly using *post-show* data to predict pre-show outcomes. **This is a methodology bug** in my Q07 signal (iii) hospitality_overrun.

(Query: `q10_audit_assumptions.py` (b))

## D27. CORRECTED BACKTEST BASELINE: 45.8% (not 54%).

> ⚠ **Further superseded by D27.1.** Q11 added predictive variants of signals (ii) and (iii) and re-ran on the full 24 disputes. Final Wednesday-honest baseline = **41.7%** (10/24). The 45.8% below was the interim after dropping signal (iii) but before adding signal (ii.pred) / (iii.pred).

Of the 2 disputes caught only by signal (iii) (Kerosene Kid 2025-03-06, Ledger 2025-04-05), removing the signal as "not Wednesday-honest" drops recall:

| Variant | TP | FN | Recall |
|---|---|---|---|
| All 5 signals (original Q07 number) | 13 | 11 | 54.2% |
| **Wednesday-honest signals only (i, ii, iv, v + ii.pred)** | **11** | **13** | **45.8%** |

**Memo framing:**
> *"Heuristic Wednesday-predictive baseline: 41.7% recall on historical disputes. Audit-only signals add 12 points but require expense-pipeline currency the venue doesn't maintain today — surfacing that absence is itself a product requirement. LLM-extracted ambiguity (signal i) is the named target to lift baseline above 60%."*

The honesty cost (41.7 vs 54) is a memo strength, not a weakness.

(Query: `q11_backtest_corrected.py`; original (inflated) numbers from `q07_build_prep.py` (d))

## D27.1 — Corrected Wednesday-honest backtest (Q11, replacing Q07 numbers)

Signal set, after applying the Wednesday-knowability filter (issue 4):

| Signal | Wed-honest? | Recall | Fire-rate on paid |
|---|---|---|---|
| (i) Ambiguous prose (regex baseline) | ✅ | 17% | 5% |
| (ii.pred) Recoup risk from history | ✅ | 4% | 4% |
| (iii.pred) Hospitality overrun history | ✅ | 4% | 3% |
| (iv) Ignored structure | ✅ | 25% | 11% |
| (v) Prior open-loop notes | ✅ | 4% | 8% |
| **ANY signal fires** | — | **41.7%** | **23.6%** |

**Of the 2 hidden future disputes (D18):**
- ✅ Sunday Drivers 2026-07-01 — caught by signal (iv) tier_ratchet
- ✗ House of Lights 2026-06-10 — MISSED. The flat deal's prose doesn't have walkout/recoup language; the marketing-recoup note is in `settlements.notes`, not `deal_notes_freetext`. (The product would catch this if/when the agent's email mentioned the recoup — see email-input feature.)

**LLM target:** lift signal (i) recall from 17% (regex) toward 40%+ via semantic ambiguity reading. Expected total recall: 55–65%. Memo names this as the build's eval target.

(Query: `q11_backtest_corrected.py`)

---

## D28. Hallucination caught: source provenance must be honest, not flattering

During design discussion, I mocked an agent-facing confirmation UI with a column labeled *"from your email:"* containing quoted snippets. The quoted snippets are actually from `deal_notes_freetext` (Mariana's prose). We do not have any email in the data model for any deal except Coastal Spell (`data/dispute-thread.md`).

**Why this is worth flagging in the memo:** it's an instance of the same failure mode that produces disputes. Confident-sounding provenance for actually-ambiguous source material → downstream parties trust it → discover the mismatch later. The whole point of slice 1+3 is to make source provenance honest, not flattering. The agent-facing UI must label data by its actual source: *"from Mariana's notes"* unless and until we have the email.

This finding motivates a small but meaningful product addition (Issue 5b raised by Arshdeep): **optional email paste field on deal entry**, designed below as part of the slice 1 build. Closes the L1↔L2 gap explicitly when Mariana has the email in hand.

---

# Unstructured-text audit (D29–D34) — fields I should have queried at the start

Arshdeep noticed `agents.preferences_notes` had rich content I never queried. Ran a full audit of every text column across every table. Findings below.

## D29. agents.preferences_notes is dense per-agent operational intelligence.

> 🔍 **Arshdeep flagged the miss.** I'd read the schema on day 1 (D5 reference) and seen `agents.preferences_notes` but never queried it. Arshdeep pushed back during the DB-review pass: "go deeper on the DB; bring skepticism to anything that seems too clean." That nudge led to Q12, which surfaced this finding. The agent severity modifier signal (vii) in the production pre-flight exists because of this catch.

7 of 14 agents have notes. Verbatim content (with my interpretation):

| Agent | Agency | Note | Implication |
|---|---|---|---|
| **Daniel Hwang** | WME | *"Pushes back hard. Wrote the email thread on the Coastal Spell dispute (March 2025). **Tends to ambiguity in deal emails — worth pre-negotiating clarifications.**"* | The product can elevate ambiguity-flag severity for any deal where Daniel is the agent. The note literally tells us pre-negotiation is the right move — which is exactly the slice's value proposition. |
| **Andrea Pelletier** | WME | *"Negotiates the deals; her colleagues handle settlement."* | **Cross-agent within agency.** Andrea writes deals; Daniel handles disputes. Confirms my prior call-out that the agent-history signal needs to union by **agency**, not just agent. |
| **Sarah Kim** | WME | *"One of the easier WME agents. Reads settlements carefully but fairly. **Pet peeve: 'Miscellaneous' line items in expenses without itemization.**"* | Per-agent UX signal: when generating Sarah's settlement statement, never use "Misc" / "Other" — always itemize. |
| **Tom Neary** | Wasserman | *"Has his own settlement template he wants filled in. Annoying but he renews the relationship."* | Tom is Mariana's highest-dispute agent (11 episodes, 53 shows = 21%). The note suggests friction is at least partly template-driven. Workflow signal. |
| **Meera Patel** | CAA | *"New at CAA, took over a roster from a departing agent. Still learning our venue."* | "New agent" pre-flight signal — first interactions need extra care. |
| **Danny Ortiz** | CAA | *"Easygoing. Trusts Mariana. Quick to sign off."* | Low-friction agent — could *deprioritize* in pre-flight ranking to reduce noise. |
| **Pat Cho** | Independent | *"Books smaller indie bands. Often the artist's manager too."* | Different relationship dynamic — agent and manager are the same person. |

**Why this is meaningful for the slice:**
- Daniel Hwang's note is *literally a product spec written by Mariana for herself*. The intent of pre-flight is to do what the note says — surface ambiguity before show. We can incorporate this signal directly.
- Per-agent context is the perfect modifier for severity scoring: same ambiguous clause + low-friction agent = low severity; same clause + Daniel Hwang = high severity.
- Andrea↔Daniel cross-agent dynamic explicitly confirms the agency-join bug I flagged. Must fix in pre-flight queries.

(Query: `q12_unstructured_audit.py` (a), (f))

## D30. comps.notes has out-of-band agreement records.

143 of 1,935 comp rows (7%) have notes. Most are stock labels ("2-for-1 Tuesday promo", "Spotify pre-save campaign", "Radio giveaway"). But there's one revealing exception:

> *"Per Sarah Kim email 4/12 — agreed these count toward gross at face value. Flag s..."*

This is the **comps version of the deal-as-a-ghost problem.** An agreement about how comps count toward gross was made by email (out-of-band). Mariana captured it in a comp note. There's no structured "comp gross agreement" field. Same pattern as the marketing recoup ambiguity.

For our slice, this is a v2 extension — apply the same "structured + agreed" model to comps. Memo notes it as a natural next slice.

(Query: `q12_unstructured_audit.py` (b))

## D31. expenses.description has named marketing-recoup line items.

648 of 2,943 expense rows (22%) have descriptions. Top patterns reveal the *actual content* of recoups:

| Category | Top descriptions | Count |
|---|---|---|
| hospitality | **"Hospitality overage"** | 68 |
| marketing | **"Instagram boost"** | 126 |
| marketing | **"Local radio spot"** | 115 |
| marketing | **"Spotify ad"** | 113 |
| backline | "Backline rental" | 225 |

**The strongest finding here:** *"Hospitality overage"* is its own description string used 68 times. So Mariana DOES tag overruns in the expense system — and that's a Wednesday-knowable signal *much stronger* than my hospitality-cap math, because it's a deliberate human-labeled overage rather than a calculated one. And "Instagram boost" / "Spotify ad" expenses are the literal contents of marketing recoups that surprise agents at settlement.

**New pre-flight signal (viii):** "expense description contains 'overage' or marketing-recoup-typical descriptions" — much more precise than my regex-on-deal-prose.

(Query: `q12_unstructured_audit.py` (c))

## D32. artists.manager_email is 0/59 NULL.

Schema field exists; no rows have data. Mariana cannot DM artist managers via this channel. Not material for our slice — but worth noting we can't build any "loop in the manager" feature from this data.

(Query: `q12_unstructured_audit.py` (d))

## D33. Tom Neary is the canonical highest-friction agent.

Per-agent dispute episodes (count + rate):
- Tom Neary (Wasserman): 11 episodes / 53 shows = **21%**
- Pat Cho (Independent): 9 / 66 = 14%
- Kev Park (Paradigm): 6 / 16 = 38% (small N caveat)
- Daniel Hwang (WME): 2 / 25 = 8%
- Most others: ≤ 2 episodes

Tom is the per-agent risk to weight most. His preferences_notes confirms "his own template he wants filled in" — likely the template friction is a meaningful chunk of his dispute volume. A v2 product move could auto-export settlement statements in agent-specific templates; v1 just flags "this agent expects a custom format."

(Query: `q12_unstructured_audit.py` (f))

## D34. Cross-table validation: 7/14 agents have notes; the 7 who do are the operationally-relevant ones.

Notice that the agents with notes are the ones with meaningful dispute history (Tom 11, Pat 9, Daniel 2, Danny 1) OR are explicitly contextual (Andrea = the deal-writer, Meera = the new agent, Sarah = the friendly WME). The 7 *without* notes are the ones Mariana hasn't formed a strong opinion on. So:

- The presence-or-absence of a note is itself a signal — "Mariana has formed an opinion on this agent" = elevated context value.
- The notes themselves drive severity weighting.

---

# Design changes from Q12 findings

## New / refined signals

| # | Signal | Source | New / refined |
|---|---|---|---|
| (i) | Ambiguous prose (LLM) | `deal_notes_freetext` | Existing, severity weighted by D29 |
| (ii.pred) | Recoup risk from history | Prior settlements **union by agency** (not just agent) | **REFINED per D29 (Andrea/Daniel cross-agent)** |
| (iii.pred) | Hospitality overrun history | Prior settlements | Existing |
| (iv) | Ignored structure | Deal/bonuses | Existing |
| (v) | Prior open-loop notes | Prior settlements.notes | Existing |
| (vi) | Deal not agent-confirmed | New schema | Production-only |
| **(vii)** | **Agent flagged 'pushes back hard' / 'tends to ambiguity'** | **`agents.preferences_notes`** | **NEW from D29** |
| **(viii)** | **Marketing expense entered with no recoup in deal** | **`expenses.description` LIKE '%Instagram boost%'/'%Spotify ad%'**  | **NEW from D31, MUCH stronger than regex** |
| **(ix)** | **New agent / never-settled-with-us-before** | **`agents.preferences_notes` mentions 'new' OR no prior settlements with us** | **NEW from D29 (Meera Patel)** |

Severity modifier (cross-cutting): per-agent preferences_notes content scales the severity of *any* other firing signal. Daniel + ambiguity = high; Danny + same ambiguity = low.

## Mariana review UI: surface the per-agent note

When Mariana reviews an LLM-extracted deal for a Daniel Hwang show, the surface should show:
- The standard prose ↔ extracted side-by-side
- **A persistent banner at the top**: *"Daniel Hwang (WME) — your notes: 'Pushes back hard. Tends to ambiguity in deal emails — worth pre-negotiating clarifications.'"*

The agent-context note is literally already in the system. Surfacing it on the deal page is a 30-minute build addition with high craft impact.

## Eval set: add Tom Neary case

Tom is the highest-dispute agent and has a distinctive operational pattern (template friction). Adding a Tom Neary dispute to the eval set (12 cases instead of 11) ensures the LLM is tested against his pattern. Will pick a representative case during T0.

---

# D35. Signal (viii) STRESS-TESTED AND DROPPED. Negative finding kept for memo.

Arshdeep pushed back on signal (viii) ("marketing expense in system + deal silent on recoup"): can we even tell when the expense was entered? Q13 ran a pattern test on the seeded data, independent of entry timing:

| Population | Signal (viii) fires | % |
|---|---|---|
| Disputed (24) | 16 | 67% |
| Paid/finalized (479) | 313 | **65%** |

**Lift over base rate: ~1.0x.** At The Crescent, almost every show has marketing spend, and almost no deal mentions recoup. The signal doesn't discriminate; it just labels everything as risky. **Precision 4.9% — basically equal to the dispute base rate.**

**Decision: drop signal (viii).** Adding noisy signals to bump apparent recall would be dishonest. The 41.7% baseline stays.

### Bonus discovery: "Hospitality overage" description is a TRUST signal, not a risk signal.

| Population | "Hospitality overage" description present | % |
|---|---|---|
| Disputed (24) | 2 | 8% |
| Paid (479) | 62 | 13% |

Lift = **0.64x** (reverse-correlated). When Mariana explicitly logs an overage, the show is *less* likely to dispute. Reading the data: she labels overruns transparently, absorbs them (D13), the agent has nothing to fight about later. This is operational honesty preventing disputes.

**Memo angle:** include this as a finding — *"the data revealed an unexpected reverse-correlation between explicit overage labeling and disputes, suggesting Mariana's habit of transparent absorption already buys trust. Our slice doesn't need to add a hospitality-prediction signal; the venue already handles it operationally."*

(Query: `q13_signal_viii_test.py`)

---

# Final locked signal set (after Q12 + Q13)

| # | Signal | Source | Role | Notes |
|---|---|---|---|---|
| (i) | Ambiguous prose | deal_notes_freetext | Primary firing | LLM-augmented in production |
| (ii.pred) | Recoup history | Prior settlements (union by agency) | Primary firing | |
| (iii.pred) | Hospitality overrun history | Prior settlements | Primary firing | |
| (iv) | Ignored structure | Bonuses + prose | Primary firing | |
| (v) | Prior open-loop notes | Prior settlements.notes | Primary firing | |
| (vi) | Deal not agent-confirmed | New schema | Primary firing | Production-only |
| (vii) | Agent severity modifier | agents.preferences_notes | **Multiplier** — not standalone | New from D29 |
| (ix) | New-to-venue agent | agents.preferences_notes OR no prior shows | Informational badge | New from D29 |
| ~~(viii)~~ | ~~Marketing expense + silent deal~~ | ~~expenses.description~~ | **DROPPED** | Lift 1.0x — not discriminative |

**Baseline (heuristic): 41.7% recall on 24 historical disputes.** LLM target: lift signal (i) recall from 17% → 40%+, pushing total toward 55–65%.

---

# Design refinements (issues raised by Arshdeep)

## Add HITL state machine to slice 1 (Issue 2)

State machine per deal:
- `prose_entered` (Mariana writes) → `extracted_draft` (LLM produces structure)
- `extracted_draft` → `mariana_confirmed` (Mariana reviews per-field with source spans + confidence)
- `mariana_confirmed` → `agent_pending_review` (shareable link sent)
- `agent_pending_review` → `agent_confirmed` OR → `disputed_field` (per-field agent action)
- Any amendment → `amended` → back to `extracted_draft`

Until `mariana_confirmed`, **no downstream consumer uses the structured deal** — pre-flight surfaces "deal pending booker review" rather than firing on extracted-but-not-confirmed values.

## Add amendment versioning (Issue 3)

New schema: `deal_versions` table (version_number, changed_at, changed_by, previous/new value JSON, agent_reconfirm_required boolean). Every change to a deal creates a new version; agent re-confirmation is required by default.

**Open product question for the memo:** should every amendment trigger agent re-confirmation, or only material ones (changes to guarantee, percentage, caps above $X)? This is a user-research question — added to `notes/assumptions.md`.

## Replace JSON with plain-English agent UI (Issue 5)

Agent confirmation surface is a **restatement** of the email with source quotes per term, ambiguity flags as plain-English two-reading questions (with dollar diff between readings shown), and per-item confirm/flag buttons. JSON is the substrate; the UI is what the agent sees.

## Add signal (vi): "deal not agent-confirmed" (Issue from prior turn)

Surfaces on Wednesday: *"3 of your 5 upcoming shows have structured deals that no agent has confirmed. Send the confirmation link now."*

## Mariana's structured-field workflow (Issue 1)

Structured fields are **auto-populated by LLM + reviewed by Mariana**, not mandatory at entry time. Mandatory fields produce garbage; auto-populated + reviewed produces structure without coercion.
