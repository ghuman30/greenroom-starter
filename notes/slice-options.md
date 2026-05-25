# Candidate Slices

**Final pick: 1 + 3 (deal capture & disambiguation + Wednesday pre-flight). See the memo for what shipped.** The analysis below is the pre-decision evaluation that got me there — kept on file because the rubric explicitly asks candidates to defend their cut, and the right way to defend a cut is to show the alternatives you considered.

The brief lists six adjacent problems wearing the "settlement" label. Below is a one-paragraph cut on each, with the case evidence pulling toward it and the AI-leverage angle.

The brief also says: *"Pick one slice — or a tightly coupled pair."* So pairs were fair game — and I picked a pair.

| # | Slice | Core question | Strongest evidence | AI leverage | Risk |
|---|-------|---------------|--------------------|-------------|------|
| 1 | **Deal modeling** | Make the deal a structured, shared, unambiguous artifact between venue + agency | Sarah `sarah-kim.md:29,33`; Mariana `mariana.md:112`; Marcus `marcus.md:55`; Diego `diego.md:21`; the entire Coastal Spell thread | High — LLM extraction from prose + ambiguity detection on phrases like "marketing recoup against gross" | Easy to over-build the structured schema. Has to coexist with `notes_freetext` reality. |
| 2 | **Audit trails / 2am paper trail** | Capture what was discussed and agreed during settlement so disputes have a record | Mariana `mariana.md:61` ("no record of what happened in the room"); brief's planted "Disputed badge with positive sign-off" | Medium — could auto-summarize the conversation, classify which line items were contested | Risks turning into a meeting-notes app. Doesn't address upstream cause. |
| 3 | **Real-time prediction / Wednesday pre-flight** | Surface what will go wrong at 2am on Wednesday, while it's still cheap to fix | Mariana `mariana.md:59` ("knowable on Wednesday"); Marcus `marcus.md:55` ("clean or messy"); Sarah `sarah-kim.md:33` | High — anomaly detection across deal/expenses/comps + LLM classification of deal-language risk | Risk of being a dashboard nobody opens. Needs to push, not pull. |
| 4 | **2am walkthrough conversation** | Make the in-person settlement conversation efficient and trustworthy | Diego `diego.md:25,43`; Mariana `mariana.md:37` ("show your work") | Medium — could surface anomalies inline ("hospitality $400 over cap"), generate plain-language explanations | The "Vs-deal calculator" trap lives here. Easy to slide into building the calculator everyone says we shouldn't lead with. |
| 5 | **Post-show agent communication** | The Saturday-morning artifact the agent reads — itemized, traceable, defensible | Sarah `sarah-kim.md:43,55`; Diego `diego.md:43` ("pre-review on the drive") | High — LLM drafting of explanation prose + provenance rendering | Doesn't fix root cause of disputes (ambiguous deals). Could be a thin layer on top. |
| 6 | **Dispute resolution** | A workflow for when settlements are contested — the email-thread replacement | The entire Coastal Spell thread; Mariana `mariana.md:55` (40% of settlements have pushback) | Medium — LLM summarization of dispute thread + position-tracking | Lagging indicator. Brief explicitly hints upstream is better leverage. |

---

## Tightly-coupled pairs worth considering

- **1 + 3** — Structured deal + Wednesday pre-flight. (Same upstream artifact, two different surfaces it powers. Each makes the other more believable.)
- **1 + 5** — Structured deal + agent-facing settlement statement. (Closes the loop between negotiation and settlement. Sarah's three asks in `sarah-kim.md:55` are literally these two slices.)
- **3 + 4** — Pre-flight + 2am surface. (Same anomaly-detection engine, two contexts. Wednesday warning becomes Friday checklist.)

---

## The "Vs-deal calculator" trap (the slice we should NOT lead with)

The most obvious cut is "ship Vs-deal math in the in-app tool." Evidence:
- README: vs deals are 33% of all deal mix (`README.md:108`).
- Mariana: 70% of her deals are vs (`mariana.md:33`).
- Brief: 62% of Crescent deals can't be settled in-app.
- The current `lib/dealMath.ts` literally returns `{ supported: false }` for vs.

It's tempting because the gap is enormous and obvious.

**Why it's the wrong lead:**
1. Pri's memo explicitly diagnoses *comprehensive but mediocre* — building more deal math is more *comprehensive*, not more *crafty*. (`ceo-memo.md:21,37`)
2. It doesn't show "Applied AI" thinking. It's deterministic engineering with no AI leverage. The role description specifically rewards AI as senior teammate.
3. Even if we shipped it, every transcript says the trust problem is upstream of the math. Sarah: "the math is the easy part."
4. Marcus says it directly: ambiguity tax is paid even when the math is right.

So if vs-deal math is in our slice, it's because it's a forcing function for something else — not the headline.

---

## What I picked — and why

**1 + 3: Structured deal capture + Wednesday pre-flight risk surface.**

- Single shared artifact: an "Agreed Deal" object built from prose, with structured terms, an ambiguity score per clause, and a shared link the agent confirms before show.
- Wednesday pre-flight reads from the same artifact + ticket/expense state + agent-confirmation state and ranks upcoming shows by risk.
- AI is load-bearing for ONE specific job — semantic ambiguity reading on signal (i) — not sprinkled everywhere. Signals (ii)–(v) are deterministic SQL/regex over history.
- Evals are concrete: 12-case hand-labeled set for extraction quality, 537-show backtest for Wednesday-honest recall.

**The honest tradeoff I accepted:** the slice does *nothing* for the 2am math problem. I cut audit trails, dispute UI, the 2am walkthrough, and the Vs-deal calculator. The argument: "fix the upstream cause; the 2am tool gets easier downstream — and the slice ships within budget at depth, not breadth."

This is also what I defend in the memo, with measured numbers and the dropped signal (viii) as the credibility marker on the recall number.
