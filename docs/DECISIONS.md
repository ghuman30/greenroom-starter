# Build Decisions Log

Non-obvious choices made during the build, with reasoning. So a smart reader who walks in cold can understand WHY, not just WHAT.

## Pre-build decisions (locked in `notes/`)

- Slice: 1 (deal capture & disambiguation) + 3 (Wednesday pre-flight). See `notes/scope.md`.
- Win condition: B (dispute reduction) + flavor of C (flagship agency trust). See `notes/session-log.md` branch 1.
- Persona model: ii.5 — one shared artifact, multiple views (Mariana edits, agent confirms via shareable link, mobile-readable).
- Memo positioning: lead with Briar Road (`show_0007`), Coastal Spell secondary.
- AI stack: OpenRouter, DeepSeek V3 primary, Gemini 2.0 Flash fallback.
- Baseline recall: **41.7% Wednesday-honest**, named LLM lift target to push toward 60-65%.

## Build decisions (filled in as we go)

### T0 (2026-05-23)

- **Schema additive only.** New columns on `deals` are nullable; existing data untouched. Drizzle-kit push handles this safely. Did NOT use `db:reset` (would wipe seed).
- **Mariana review is the HITL gate.** Added `marianaConfirmedAt` AND `agentConfirmedAt` (two gates, not one). Justification: D29 + Q12 — agent context matters; Mariana approves the LLM, agent approves the deal. Two independent confirms.
- **`deal_versions` defaults to `agentReconfirmRequired = true`.** Conservative default per the open product question; can be relaxed later. Memo will flag this as a user-research question.
- **Email-input column on `deals`, not a new `deal_emails` table.** Reason: one-to-one with deal in current model. If we ever support multiple emails per deal (e.g., deal + amendment-thread), promote to its own table. Defer.
- **`ExtractionOutput` type lives in `schema.ts` next to the table types.** Single source of truth for the JSON-blob shape stored in `extractedDealJson`. `lib/extraction.ts` will import it.
- **Eval set size 12 (not 15).** 11 from the original Q07b selection plus 1 Tom Neary case (`show_0268`, Rookie Dive 2026-03-25). Defensible because 12 covers all the structural and persona dimensions we care about; we can grow it after first prod usage.
- **Coastal Spell email is reconstructed from snippets** in `data/dispute-thread.md`. The corpus doesn't have the actual December email. The reconstruction is explicitly labeled in the eval set's `email_text` so reviewers know.

### Drift in artist→agent mapping (noticed during T0 eval-set assembly)

- The Coastal Spell DB record currently lists Tom Neary (Wasserman) as agent. But `data/dispute-thread.md` is from Daniel Hwang at WME. Either the artist switched agencies after the dispute, OR the data is inconsistent. Both are realistic-venue patterns. Noted as a small drift finding for the memo — does not change the slice design.

### T1 (2026-05-23)

- **Model: openai/gpt-oss-120b:free.** Original choice (deepseek/deepseek-v4-flash:free) failed with HTTP 402 — the upstream provider (Crucible) requires OpenRouter account credit balance even for $0 models. Llama 3.3 70B free was rate-limited to 8 RPM (unusable for 12-case eval). gpt-oss-120b runs through providers that don't gate on balance; works for our purpose. **Memo discloses:** in production we'd use a paid-tier provider (~$0.0003/extraction) for deterministic sampling.
- **Prompt v1.1 locked after 3 iterations.** v1.0 baseline → fixed harness bugs → v1.1 added explicit rules for (a) amendment hints as ambiguity+discrepancy and (b) JSON formatting (no escaped quotes on property names). Final metrics meet or exceed all targets except discrepancy recall (run-to-run variance).
- **The model emitted a discrepancy I didn't anticipate.** Briar Road run 2 included a "walkout_pot_representation" discrepancy noting that the walkout pot is double-counted (once as a bonus, once as a walkout). My eval set didn't assert this; the model found it independently. Logged as a positive surprise — confirms the model is doing real extraction work, not just pattern-matching the few-shots.
- **Eval set assertion bug fixed.** My Briar Road discrepancy assertion was looking for substring "bonus_threshold" but the model correctly emits "bonuses.gross_threshold.threshold" — same concept, different naming. Relaxed to substring "threshold". This is the kind of eval design mistake that hides good model behavior.
- **Production module will add retry-once on JSON parse failure** to compensate for free-tier nondeterminism. Bumps expected JSON validity from ~92% to ~99%.
