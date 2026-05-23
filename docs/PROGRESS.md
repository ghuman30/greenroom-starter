# Build Progress

Tracks tracer-bullet build phase. For case-study analysis (evidence, scope, slice rationale), see `notes/`.

## Tracers

| # | Tracer | Status | Notes |
|---|---|---|---|
| T0 | Schema migration + extraction-set hand labels | **DONE** (pending spot-check) | Schema applied via `npm run db:push`. 6 columns added to `deals` + `deal_versions` table. ExtractionOutput TS types added. Eval set of 12 cases hand-labeled at `notes/eval_set_with_labels.json`. **Awaits user spot-check of Coastal Spell + Sunday Drivers + Tom Neary labels before T1 starts.** |
| T1a-c | Extraction prompt + Python eval harness | **DONE** | Prompt v1.1 locked. Final eval results on openai/gpt-oss-120b:free across 3 runs: field accuracy ~99%, ambiguity recall **100%**, ambiguity precision **100%**, recoup recall **100%**, discrepancy recall ~70% (variance), JSON validity ~92% (one random failure per run). Run-to-run variance is free-tier model nondeterminism, not prompt quality. Will mitigate with retry-on-failure in T1d production module. Original model (`deepseek/deepseek-v4-flash:free`) was inaccessible due to Crucible provider requiring account credit balance. Llama 3.3 70B free was rate-limited to 8 RPM (unusable). `openai/gpt-oss-120b:free` is the working free-tier option. |
| T1d | TS production module (lib/extraction.ts) + reviewer pass | **DONE** | Mirrors Python harness; reads same `lib/extraction-prompt.md`. kieran-typescript-reviewer flagged 7 issues, all fixed: renamed `ExtractionError.cause` → `reason` (use standard `cause` slot for chaining); added `ExtractionParseError` for retry gating (retry now ONLY on parse failures, not auth/rate-limit/timeout); dropped `reasoning` fallback (it's CoT, not the answer); added `isExtractionOutputShape` runtime guard; made metadata fields optional in `ExtractionOutput` type; `persistExtraction` now uses `.returning()`; `getExtraction` returns discriminated `LoadedExtraction` result. TS compiles clean. Same `reasoning`-fallback bug also fixed in `notes/eval_harness.py` for parity. |
| T2 | Mariana review UI (`/shows/[id]/deal`) | not started | Side-by-side prose ↔ extracted, per-field confirm |
| T3 | Agent confirmation surface (`/deal/[token]`) | not started | Plain-English restatement, source-honest labels |
| T4 | Wednesday pre-flight (`/preflight`) | not started | Ranked upcoming shows; re-run Q11 backtest with LLM signal (i) |

## Definition of done per tracer

- Tracer is end-to-end on at least one demo show
- Compound-engineering reviewer pass complete
- Tests (eval harness or agent-browser) green
- PROGRESS.md updated
- DECISIONS.md logs any non-obvious choices
- ISSUES.md logs anything deferred or surprising
