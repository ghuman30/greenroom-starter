# Session State — Greenroom Case Study

Dense state-capture for context resumption. Lives in `notes/` (held local
per the code-public/notes-local convention). Sister file in `docs/`
captures the same shape but at less detail for the public fork.

**Project**: Greenroom Applied AI PM case, customer The Crescent, slice =
deal capture + Wednesday pre-flight.

**Branch**: `slice/deal-capture-preflight` on `origin` (=
`git@github.com:ghuman30/greenroom-starter.git`).

**Date**: 2026-05-23.

---

## Locked decisions (do not relitigate)

| Decision | Value | Source |
|---|---|---|
| Win condition | B (cut disputes / dollar concessions) + flavor of C (flagship agency trust) | `notes/session-log.md` branch 1 |
| Persona model | **ii.5** — one shared artifact, multiple views (Mariana edits, agent confirms via shareable link, mobile-readable) | branch 2 |
| Slice cut | **1 (deal capture & disambiguation) + 3 (Wednesday pre-flight)** | branch 3 |
| Memo positioning | Lead with **Briar Road** (`show_0007`), Coastal Spell secondary | branch 3.5 |
| AI model (eval + prod) | `openai/gpt-oss-120b:free` on OpenRouter (DeepSeek V4 wanted credit balance; Llama 3.3 70B rate-limited at 8 RPM) | branch T1 |
| Build approach | 4 tracer bullets (T1–T4), reviewer-pass after each, `docs/` tracking | branch 3.7 |
| HITL | Two independent gates: `marianaConfirmedAt`, `agentConfirmedAt` | T2 |
| Email-input | Optional paste field on deal; LLM treats email as primary when present | branch 3.7 |
| Amendment policy | Every change requires agent re-confirmation (relaxable per venue) | branch 3.7 |

---

## Eval baselines (final)

**Heuristic Wednesday-honest backtest** on 24 historical disputes (Q11):
- Recall: **41.7%** (10/24)
- Precision: 8.1% (10/(10+113))
- Fire-rate on paid/finalized: 23.6%

**LLM extraction eval** on 12 hand-labeled cases (gpt-oss-120b, 3 runs):
- Field accuracy: **~99%** (typical 100%; one run 98.5%)
- Ambiguity recall: **100%** (consistent)
- Ambiguity precision on clean cases: **100%**
- Recoup recall: **100%**
- Discrepancy recall: ~70% (variance run-to-run)
- JSON validity: ~92% (one failure per run; free-tier nondeterminism)

**Memo number to lead with: 41.7%** Wednesday-honest + LLM lift target of
55-65% (signal i moves from 17% regex → 40%+ LLM).

---

## Hero examples & memo narrative threads

| Thread | Hero | Where it lives |
|---|---|---|
| The dispute mechanism | **Coastal Spell** marketing recoup (`show_coastal_spell_dispute`) — $720 + agency trust lost to one ambiguous sentence | `data/dispute-thread.md`; D2 |
| The amendment-in-prose pattern | **Briar Road** (`show_0007`) — Mariana's note `"structured field still reflects original $11,000 — confirm before settlement"` is the case in one record. Disputed on production_overage (not marketing) — proves slice isn't narrow-cast | D9 |
| The dashboard ≠ reality reframe | **Sunday Drivers 2026-07-01** (Paradigm vs+ratchet, hidden) + **House of Lights 2026-06-10** (flat with marketing recoup, hidden). UI says "22 disputed"; reality is 24 with 2 in-flight | D18-D21; clarified post-Chrome check that this is a *missing capability*, not a bug |
| The state-drift theme | Coastal Spell DB shows status=`disputed` but `total_to_artist`=$12,285 (the resolved figure) | D6 |
| The relationship-intelligence finding | `agents.preferences_notes` — Daniel Hwang note says *"Tends to ambiguity in deal emails — worth pre-negotiating clarifications"* — literally a product spec | D29 |
| The dropped signal (credibility move) | **Signal (viii) dropped** after Q13 stress-test: fired on 65% of paid shows, precision 4.9% (≈ base rate). Memo headlines this as "we measured carefully" | D35 |
| The unexpected reverse-correlation | "Hospitality overage" descriptions are *negative* indicators of dispute (lift 0.64x) — Mariana's transparent absorption habit buys trust | D35 |

---

## Build progress

### Done
- **T0**: schema additions (extracted_deal_json, agent_email_text + received_at, mariana/agent confirmedAt, confirmed_by_agent_id) + `deal_versions` table + ExtractionOutput types in `db/schema.ts`. 12-case eval set hand-labeled at `notes/eval_set_with_labels.json`.
- **T1**: `lib/extraction-prompt.md` (system + 4 fewshots) + `notes/eval_harness.py` + `lib/extraction.ts` (production module with retry-on-parse-failure, runtime shape guard, discriminated `LoadedExtraction`, `parseBonuses` helper). 6 kieran-typescript-reviewer fixes applied.
- **T2**: `/shows/[id]/deal` page + Server Actions + DealReviewActions client component. Side-by-side prose↔extracted, ambiguity flags with $-deltas, discrepancy display, agent preferences_notes banner. Nav link added from `/shows/[id]`. 6 reviewer fixes applied (7th was conditional on React 18, N/A).

### Pending
- **T3**: `/deal/[token]` agent confirmation surface. Plain-English restatement, per-item confirm/flag, mobile-readable. New schema: `deal_confirmation_tokens` + `deal_agent_responses` tables.
- **T4**: `/preflight` Wednesday surface. Ranked upcoming shows with risk flags from the 8 locked signals (i, ii.pred, iii.pred, iv, v, vi, vii modifier, ix info). Re-run Q11 backtest with LLM-flagged ambiguity replacing regex signal (i).
- **Memo + Loom**: 1-2 page memo + 5-10 min Loom.

### Demo data populated
11/12 demo extractions populated into `deals.extracted_deal_json` via
`notes/populate_demo_extractions.py` from last eval run. Briar Road
(show_0007) was missing — its eval had a JSON parse error that run.
**Action item for the user**: re-run `python -X utf8 notes/eval_harness.py`
then `python -X utf8 notes/populate_demo_extractions.py` to repopulate.

---

## User preferences (case-style)

| Preference | Value |
|---|---|
| Commit split | **Code → fork, notes → local**. `lib/`, `app/`, `db/`, `docs/`, `data/greenroom.db`, `.env.example`, `.gitignore` go public. `notes/` (eval harness, queries, this file) stays local. |
| Commit cadence | **Single commit per tracer** (not split into multiple). |
| Push cadence | **User pushes manually** in Git Bash (SSH key has passphrase; bash tool can't type it). |
| Reviewer cadence | **`kieran-typescript-reviewer` after each tracer**, apply all reasonable fixes before commit. |
| Slice flexibility | **Locked.** Don't reopen slice cut unless data forces it. |
| Spot-check protocol | User spot-checks Coastal Spell + Sunday Drivers + Tom Neary for eval correctness. |
| Memo number policy | **Honest baseline (41.7%)**, not inflated. Document dropped signal (viii) as credibility move. |
| Branch | `slice/deal-capture-preflight` on personal fork `ghuman30/greenroom-starter`. |
| Auth | SSH ed25519 (`~/.ssh/id_ed25519_ghuman30`) with passphrase. `OPENROUTER_API_KEY` in `.env.local`. Model: `openai/gpt-oss-120b:free`. |

---

## Reproducibility commands

```bash
# From repo root:
cd ~/github2/learnings/clipboard_health/case-cloned

# Schema migration (apply current schema.ts to local db)
npm run db:push

# Reseed from scratch (DESTROYS local db)
npm run db:reset

# Run dev server
npm run dev   # http://localhost:3000

# Run LLM eval (12 cases against gpt-oss-120b:free)
python -X utf8 notes/eval_harness.py

# Populate demo extractions from latest eval results
python -X utf8 notes/populate_demo_extractions.py

# Re-run Wednesday-honest backtest (heuristic baseline)
python -X utf8 notes/queries/q11_backtest_corrected.py

# Full app-vs-DB audit
python -X utf8 notes/queries/q08_app_vs_db.py

# List available free models on OpenRouter
python -X utf8 notes/list_free_models.py
```

---

## Open questions for memo

Already logged in `notes/assumptions.md`. Headlines:

- **Sarah/agent**: should every amendment trigger re-confirmation, or only material ones? (Drives signal vi behavior.)
- **Mariana**: when do hospitality / production / sound costs actually get entered? (Drives data-currency requirements; honestly disclosed.)
- **Marcus/GM**: agent unresponsiveness policy — default state when no agent action by show − N days?
- **Sarah**: settlement template formatting preferences (Tom Neary's template, Sarah's "no Misc" rule per `preferences_notes`).

---

## Memo target structure (1-2 pages)

| Section | Words | Key points |
|---|---|---|
| **Slice & why this one** | ~150 | "Settlement is several adjacent problems. We picked deal capture + Wednesday pre-flight because three of four interviews independently named ambiguity as the root cause." Briar Road as the canonical case. |
| **What we built** | ~300 | LLM extraction (slice 1 spine) — production code + eval harness + 4-shot prompt. Mariana review UI + agent confirmation link (ii.5). Wednesday pre-flight surface (slice 3) with 8 signals. |
| **What we measured** | ~250 | Eval set of 12 hand-labeled cases. Field accuracy ~99%, ambiguity recall 100%, JSON validity ~92%. Wednesday-honest backtest: 41.7% recall (8/8 signals after dropping noisy signal viii). LLM target lifts toward 55-65%. |
| **What we cut and why** | ~200 | Vs-deal calculator (Pri's "comprehensive but mediocre" trap), dispute-resolution UI (lagging), audit-trail capture (more theatre), full settlement statement (natural v2). Signal viii dropped after stress-test. |
| **What we'd ship next** | ~150 | Email forward-to-address ingestion (v2). Settlement statement as shared doc (Sarah's full three asks). Per-agent template export (Tom Neary). Per-venue pre-flight cadence config. |
| **What we'd validate** | ~150 | Re-run backtest with venue's actual expense-entry currency. A/B agent re-confirmation cadence with 5 venues. Track ambiguity-flag → dispute prevention conversion. |

---

## Loom outline (5-10 min)

1. **00:30** — open `/shows`, point to "22 disputed" stat. "What we'll do: surface the 2 disputes hidden behind this number and prevent them next time."
2. **01:30** — open `/shows/show_coastal_spell_dispute/deal`. Walk through: agent context banner (Tom Neary), prose↔extracted side-by-side, source spans, ambiguity flag with $720 delta, two readings.
3. **02:30** — same page, scroll to discrepancy and low_confidence. "This is what the LLM emits when it's honest about uncertainty."
4. **03:30** — `/shows/show_0007/deal` (Briar Road). "Mariana literally wrote a note to herself in the prose. The extractor surfaces it as a discrepancy + ambiguity flag. This is the *system* doing what Mariana already does manually."
5. **05:00** — `/preflight` (T4 surface). Show the 5 upcoming shows with risk flags. Sunday Drivers 2026-07-01 surfaces with tier_ratchet + history flags. "The dashboard says no Paradigm disputes; pre-flight says one is incoming."
6. **06:30** — terminal: `python notes/eval_harness.py`. "We built the test before we shipped. 100% ambiguity recall, ~99% field accuracy on 12 hand-labeled cases."
7. **08:00** — backtest re-run with LLM signal. "Heuristic baseline 41.7%. With LLM-extracted ambiguity replacing regex, signal (i) lifts to X%. Total recall: Y%."
8. **09:00** — recap + what's next. "We measured before we shipped. We dropped a signal that didn't earn its place. We're not claiming we solved settlement — we picked a slice and went deep."

---

## Critical files map

```
lib/
  extraction-prompt.md     Shared system prompt + 4 fewshots
  extraction.ts            Production LLM module (OpenRouter, retry, validation)
  dealMath.ts              Pre-existing settlement engine (NOT MODIFIED)
  queries.ts               Pre-existing data layer (NOT MODIFIED — uses past-only filter)

app/shows/[id]/
  page.tsx                 Show detail (added "Review deal" link)
  deal/page.tsx            Mariana review surface (T2)
  deal/actions.ts          Server Actions for T2
  deal/DealReviewActions.tsx  Client component for T2
  settle/                  Pre-existing settle page (NOT MODIFIED)

app/deal/
  [token]/page.tsx         T3 — TO BUILD

app/preflight/
  page.tsx                 T4 — TO BUILD

db/
  schema.ts                Drizzle schema (T0 additions + ExtractionOutput types)

data/
  greenroom.db             SQLite with 11/12 demo extractions populated

notes/
  evidence.md              35 findings (D1–D35), all with citations
  scope.md                 In/out/cut for the slice
  assumptions.md           Open questions + assumptions
  slice-options.md         The 6 slice candidates analyzed
  session-log.md           Chronological branch log
  session-state.md         THIS FILE
  eval_harness.py          Eval runner
  eval_set_with_labels.json  12 hand-labeled cases
  eval_results.json        Latest eval output
  populate_demo_extractions.py  Populates extracted_deal_json from eval results
  list_free_models.py      Probe for currently-free OpenRouter models
  queries/q01-q13          DB skepticism scripts (all reproducible)

docs/
  PROGRESS.md              Tracer status
  DECISIONS.md             Build decisions log
  ISSUES.md                Known issues / deferrals

.env.local                 OPENROUTER_API_KEY (gitignored)
.env.example               Template (committed)
```

---

## How to resume from fresh context

1. Read `notes/session-state.md` (this file) for state.
2. Read `notes/scope.md` for what we're building.
3. Read `notes/evidence.md` for what the data says.
4. Read `docs/PROGRESS.md` for what's done / pending.
5. Run `git log --oneline -5` to see commit history.
6. Last completed: T2 (Mariana review UI). Next: T3 (Agent confirmation surface).

Resume with: **"T3 build start — agent confirmation surface at `/deal/[token]`."**
