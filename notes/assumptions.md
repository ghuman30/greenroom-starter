# Assumptions & "Questions I'd Ask In Real Life"

Both lists exist because the hiring rubric explicitly rewards them:
> "We are far more interested in your reasoning than your conclusion. Show your work. Explain your tradeoffs. Call out assumptions. Write down the questions you would ask in real life and tell us how the answers would change your approach."

---

## Assumptions made to unblock progress

(With "if wrong, what breaks" so the reviewer can see what's load-bearing.)

| Assumption | If wrong, what breaks |
|---|---|
| **`deal_notes_freetext` is Mariana's source of truth, not the structured columns.** | Slice 1's spine collapses — if structure is canonical, the LLM extraction adds nothing. Validated empirically (D5: 0/537 freetext is NULL; structured is 29–76% NULL; Mariana's transcript at `mariana.md:33` confirms she enters deals as prose). |
| **Mariana enters marketing/production expenses *before* show.** | Signal (iii.pred) loses signal. Marketing campaigns are paid at launch (pre-show), so true for marketing; hospitality is post-show realized — signal (iii.pred) is history-based to hedge. (D25/D26 surface the timing artifact.) |
| **Agents will actually click the confirmation links.** | If <50% engagement, signal (vi) fires on most upcoming shows and trust degrades. Mitigation: track click-through over 30 days; tune signal threshold. Real validation needs production usage. |
| **`agents.preferences_notes` is maintained by Mariana with operational intent.** | If notes are stale or one-off, agent severity modifier mis-scales. Empirical check (D34): 7/14 agents have notes — and the 7 are the ones with substantive dispute or contextual history. So the field IS maintained, just sparsely. |
| **Free-tier `openai/gpt-oss-120b:free` quality holds for production scale.** | If quality drops or rate-limits hit, fall back to paid-tier (`anthropic/claude-sonnet-4.5` ~$0.003/extraction, ~$50/venue/yr at scale). |
| **The HITL link will be opened by the actual agent, not by Mariana on the agent's behalf.** | Today the model is trust-by-possession. Mariana could submit on the agent's behalf; the audit log would still record her browser. Mitigation deferred to v2 (magic-link / SSO / signed receipts). Documented in `docs/ISSUES.md`. |

---

## Questions I'd ask in real life (and how the answer changes the design)

### To Pri (CEO)
- *"You said settlement is the Q1 craft bet. Is the win condition (a) move the 18%-active number, (b) reduce dispute volume on a representative set of large accounts, or (c) get N specific WME/CAA flagship rooms to settle in-app?"*
  - **Why it matters:** A north-star metric of "active usage %" pushes us toward a calculator that handles every deal type. A metric of "dispute volume" pushes us upstream to deal clarity. A metric of "flagship agency trust" pushes us to multi-party (agent-facing) features. They are different products.

### To Mariana (booker)
- *"When the deal email is 80 words and ambiguous, do you ever push back on the agent before signing? What stops you?"*
  - **Why it matters:** If she's already comfortable pushing back, then a Wednesday pre-flight tool just gives her a better artifact to push with. If she isn't comfortable, the tool needs to do more of the social work (draft the email, suggest the clarifying question).
- *"Of your last 10 disputes, how many were caused by a deal-term ambiguity vs. a data error (wrong expense, wrong gross, miscount) vs. a math error?"*
  - **Why it matters:** Splits the slice between deal-modeling (upstream) and audit-trail (downstream). Drives where leverage actually is.

### To Sarah (agent) and Diego (TM)
- *"If we showed you the math live in a shareable link before signoff, would you actually use it on the night, or only the next morning?"*
  - **Why it matters:** Decides whether "shared live settlement doc" is real or theatre. Sarah said yes; we want Diego's read too.

### To Marcus (GM)
- *"If we save Mariana 20 hrs/month and 1 in 30 disputes — which one keeps the lease?"*
  - **Why it matters:** Marcus is honest that the relationship cost dwarfs the dollar cost. That should bias us toward dispute prevention over time savings.

### To Anil (PM lead) — i.e., the rubric
- *"Is the bar a working prototype that solves one user's 2am, or a product spec that scales to 340 venues?"*
  - **Why it matters:** Brief says prototype + PRD memo + Loom. But it also says we're shipping "what feels good to Mariana." Resolve the level of generality before designing.

---

## Things we are choosing not to assume (and verifying first)

- The status-vs-signoff drift mentioned in the brief — we need to query the DB before claiming it as a problem we're solving. ✓ verified (D10)
- The deal-notes-vs-structured drift rate — same. ✓ verified (D5)
- Coastal Spell's actual record in the DB — we need to find the show and verify the dispute-thread numbers line up. ✓ verified (D6)

---

## Questions added after issue raise (Arshdeep, branch 3.7)

### To Sarah (agent) — amendment re-confirmation tolerance
- *"If Mariana drops a hospitality cap by $50, do you want to re-confirm? If she changes the bonus threshold by $5k after the original deal email? Where's the line for 'material' for you?"*
  - **Why it matters:** Decides whether amendment versioning re-confirmation is on every change or material-only. Wrong choice → either agent fatigue OR drift sneaks in via minor edits.

### To Mariana — LLM-output trust model
- *"If the LLM extracts your deal and it's wrong on 1 of 10 fields, do you want to (a) be alerted just to the wrong field, (b) re-do the whole extraction, or (c) edit inline and override?"*
  - **Why it matters:** Determines the granularity of the review UI. Field-by-field if (a) or (c); whole-deal redo if (b).

### To Sarah and Diego — Wednesday vs day-of cadence
- *"If we surfaced potential settlement issues on Wednesday, would you want a Friday-morning refresh too? Or is Wednesday enough?"*
  - **Why it matters:** Whether pre-flight is one-shot or daily until show. Affects build and the agent's email reminder cadence.

### To Mariana — expense pipeline currency
- *"Right now, when do hospitality / production / sound costs get entered into Greenroom? At purchase order time? When the invoice comes? When the show happens? Day after?"*
  - **Why it matters:** Pre-flight on expense-derived signals only works if expenses are entered as costs are incurred or known. If Mariana enters them all the morning of settlement, the pre-flight has nothing to surface. This is the operational requirement we're implicitly assuming.

### To Marcus (GM) — agent unresponsiveness fallback
- *"If we send the agent a confirmation link and they don't act on it before show, what's the venue policy? Do you ship the deal as Mariana extracted it? Default to most-conservative reading? Pause settlement until confirmed?"*
  - **Why it matters:** The slice has to handle the case where the human in the HITL loop ghosts. Default state matters for trust and for downstream signals.
