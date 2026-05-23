# Build Issues

Things we hit during build, deferred, or noticed but didn't fix. Honest log so the reader can see what we cut and why.

## Pre-build known issues (from notes/)

- Seed data has 29 future-dated settlements in impossible states. We design around real production assumptions; the seed quirk is noted in the memo as a one-liner.
- `expenses.entered_at` has 3 distinct values in 2,943 rows (D25). Our pre-flight signals avoid expense-timestamp dependencies; we treat expense data as a production-currency requirement, not a backtest input.
- `agent` join logic should also union by agency to handle WME's Andrea/Daniel cross-agent case. Tracked for T1 query implementation.

## Build issues (filled in as we go)

(empty)
