# Task prompt: T-078 Final number check on the finished UI

> Prepared for: Member 2 · Date: 2026-11-15 · Based on main @ 701c3a7 (T-070 to T-074, T-083 to T-085, T-087 to T-089 merged)
> Source of truth: `docs/TASK_TRACKER.md` row T-078 (PR #74): "Re-run the T-026 checker and the browser pass after T-070 to T-074 merge; update `docs/NUMBER_INVENTORY.md` with Member 3 if displays moved", and the Lead's real-data rule on PR #75.

## Task
Re-verify every number the finished UI displays against the products: the checker part (`python pipeline/number_check.py`, run separately) and a browser pass on the real app and API for everything new or changed since T-026: the summary card and sparkline, the month picker, the story chips and captions (`featured.ts`), the Analytics tab (annual sums, season band, rank, coverage, compare), the methods page results, the source lines, the imagery controls and the India outline. Update `docs/NUMBER_INVENTORY.md` for displays that moved or are new, and report the results.

## Files
Create: `docs/validation/T-078-final-number-check.md`. Modify: `docs/NUMBER_INVENTORY.md`. App code, products, thresholds and methods are not changed; a mismatch is reported, not fixed.

## Requirements
1. Each new number is compared with an independent query on the products (DuckDB or pandas), read from the page in the real app (the real API on the real products), with the rounding rules of the inventory.
2. Real-data rule: `metadata.synthetic` is false, no "SYNTHETIC" text in the page, no production import of `__fixtures__`, no hard-coded sample number in the UI texts (each digit in the content files is a stored or [VERIFIED] figure or a documented constant).
3. The report lists every check (expected, shown), the totals, the notes and what a checker cannot reach.

## Git
Branch `science/T-078-final-number-check` from the latest `main`; first commit: this prompt; PR with the template and the real-data statement; never merge; human identity, no AI attribution (D-020).
