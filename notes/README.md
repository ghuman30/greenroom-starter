# `notes/` — the reasoning trail

This folder is the show-your-work behind the prototype and memo. 
---

## Reader paths

### If you have 5 minutes — read **two files**

1. **`memo_final.md`** — Argument + slice + cuts + measurements + assumptions + questions. The diagram referenced inside is `memo-diagram.png`.
2. **`evidence.md` — top section only.** The "Six findings spotlighted in the memo" table maps the memo's `D-number` references to the underlying data findings. Skim the headers (`## D1.` through `## D35.`) to see the full set of findings I logged.


### If you have 15 minutes — add **three more**

3. **`slice-options.md`** — the pre-decision evaluation of all 6 candidate slices from the brief. Why I picked 1+3 and what I considered.
4. **`scope.md`** — the locked in / out / explicitly-cut list. Notably documents Signal (viii) being dropped after stress-test (Q13) and the corrected 41.7% recall baseline (Q11).
5. **`assumptions.md`** — assumptions made to unblock progress (with "if wrong, what breaks") plus the questions I'd ask each stakeholder in real life with how the answer would change what I'd build.

These three answer the rubric's four explicit asks directly.

### If you have 30 minutes — open **two query scripts**

The memo's numbers are all reproducible from `data/greenroom.db`:

6. **`queries/q11_backtest_corrected.py`** — the Wednesday-honest 41.7% baseline. Run it and you'll see the per-signal recall breakdown and the confusion matrix.
7. **`queries/q13_signal_viii_test.py`** — the stress-test that killed signal (viii). Shows precision 4.9% ≈ base rate, lift 1.0x. The credibility marker on the headline recall number.

If you want to run everything: `python -X utf8 notes/queries/q01_shape.py` (then q02, q03, ...). Each is standalone.

### If you want to verify the LLM extraction

8. **`eval_set_with_labels.json`** — 12 hand-labeled cases (Coastal Spell hero, Briar Road second hero, Wet Cement paid-but-disputed-recoup, both hidden future disputes, clean baselines, structural variety, agency mix).
9. **`eval_harness.py`** — Python stdlib only. Reads `lib/extraction-prompt.md`, calls OpenRouter, scores against the labels. Reports field accuracy / ambiguity recall / discrepancy recall / planned-recoup recall + per-case detail to `eval_results.json`.

To re-run: set `OPENROUTER_API_KEY` in `.env.local`, then `python -X utf8 notes/eval_harness.py`. Results in 2 minutes.

---

## File inventory (everything in `notes/`)

### Memo + diagram

- `memo_final.md` — **the memo**. Final version after round-trip through `Greenroom_Case_Memo.docx` (which is held local for delivery format).
- `memo-diagram.png` — the before/after deal flow diagram referenced in the memo.

![Before vs After deal flow](memo-diagram.png)

*Figure 1 · The deal flow today (top) vs. with the slice (bottom).*

### The argument (with citations)

- `evidence.md` — **35 cited findings** (D1–D35). Stakeholder quotes get file:line refs. DB findings get reproducible queries. Memo footnotes reference these D-numbers.
- `scope.md` — what's in, what's out, what's explicitly cut.
- `slice-options.md` — pre-decision analysis of all 6 candidate slices.
- `assumptions.md` — assumptions made + questions I'd ask in real life.

### The eval (proof the LLM extraction works)

- `eval_set_with_labels.json` — 12 hand-labeled cases with expected extraction shape + ambiguity flag assertions.
- `eval_harness.py` — runs the eval against OpenRouter, scores per-case + aggregate.
- `eval_results.json` — latest run output (audit trail).
- `eval_set_candidates.json`, `eval_set_raw_data.json` — working files used while building the labels.

### The queries (every claim in the memo is reproducible)

- `queries/q01_shape.py` — corpus shape, deal-type distribution, NULL rates
- `queries/q02_seams.py` — planted seams hunt (disputed-with-positive-signoff, Coastal Spell verification, WME marketing recoup pattern)
- `queries/q03_deeper.py` — sign-off text distribution, hospitality overruns, ratchet/walkout patterns in prose
- `queries/q04_timing.py` — dispute timing relative to signoff (the 85% next-morning finding)
- `queries/q05_skeptical.py` — adversarial pass: math reconciliation, status-vs-timestamp coherence, hidden notes
- `queries/q06_followups.py` — deep dives on Coastal Spell duplicate, Wet Cement state drift, comp boilerplate
- `queries/q07_build_prep.py` — eval set candidate selection + first backtest (54% inflated)
- `queries/q08_app_vs_db.py` — app-vs-DB audit; the 22-vs-24 explanation
- `queries/q09_trace_explain.py` — verbose trace of pre-flight signals on 4 example shows (teaching artifact)
- `queries/q10_audit_assumptions.py` — found the seed-timing artifact in `expenses.entered_at`
- `queries/q11_backtest_corrected.py` — **final Wednesday-honest baseline: 41.7%**
- `queries/q12_unstructured_audit.py` — found `agents.preferences_notes`, comps notes, expense descriptions
- `queries/q13_signal_viii_test.py` — **stress-test that killed signal (viii)**; lift 1.0x finding
- `queries/q14_backtest_llm.py` — backtest with LLM signal (i) replacing regex; matches recall at current 2% coverage, projected lift at full coverage

---

The build process used `kieran-typescript-reviewer` reviewer agents after each tracer to catch type-safety and HITL state bugs. 27 reviewer-caught issues across 4 tracers; all fixed before commit. Two end-to-end state-machine bugs (T5/T6) only surfaced when I walked the full agent-flags loop manually.

---

