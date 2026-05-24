# Build Issues

Things we hit during build, deferred, or noticed but didn't fix. Honest log so the reader can see what we cut and why.

## Pre-build known issues (from notes/)

- Seed data has 29 future-dated settlements in impossible states. We design around real production assumptions; the seed quirk is noted in the memo as a one-liner.
- `expenses.entered_at` has 3 distinct values in 2,943 rows (D25). Our pre-flight signals avoid expense-timestamp dependencies; we treat expense data as a production-currency requirement, not a backtest input.
- `agent` join logic should also union by agency to handle WME's Andrea/Daniel cross-agent case. Tracked for T1 query implementation.

## Build issues (filled in as we go)

### T3 — Agent identity verification (deferred to v2)

The `/deal/[token]` confirmation surface authenticates by **possession of the
token**, not by identity. Nothing prevents Mariana from opening her own
link and submitting on the agent's behalf, or the link being forwarded to
an unintended recipient. Two classes of risk:

1. **Internal misuse** — booker fakes the agent confirmation to clear
   pre-flight signal (vi).
2. **External forwarding** — token leaks (email forward, screenshot)
   give anyone with the URL full confirm/flag rights.

Mitigations for v2 (any one would meaningfully tighten):
- Magic-link to a verified agent email address (sender = `confirm@<venue>.greenroom.io`)
- Agency-side OAuth/SSO (WME, CAA both have SSO programs)
- Click-attested receipts — first interaction prompts the agent to enter
  their email or last 4 of phone; verified against `agents.email`
- IP/geo audit on `dealAgentResponses` for ex-post anomaly detection

For the prototype we accept the trust-by-possession model and document
it. Memo flags it as a known v2 task.

### T2 / T3 — Source-span column tagging

`source_spans` in `ExtractionOutput` is a `Record<string, string>` —
the field-path → quoted-text map doesn't tag which source (email vs
notes) each span came from. Result: both source columns on Mariana's
review surface highlight the same spans. Acceptable for demo; v2
should change the type to `{ text: string; source: "email" | "notes" }`.

### Eval coverage

Only 12 of 537 deals have `extracted_deal_json` populated (the eval
set). Full-corpus extraction would lift backtest recall projections
but requires either batch backfill or waiting for new deals to flow
through. Documented honestly in memo; Q14 reports the floor.
