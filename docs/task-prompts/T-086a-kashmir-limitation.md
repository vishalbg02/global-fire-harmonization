# Task prompt: T-086a Limitation row for the Jammu and Kashmir country attribution

> Prepared for: Member 2 · Date: 2026-11-15 · Based on main (HEAD at branch creation)
> Source of truth: the Lead's comment on PR #74 (T-086 / D-033): "Now, if you have a minute: add the limitation row to `RISKS_AND_LIMITATIONS.md` (country totals for India, Pakistan and China follow FIRMS's attribution in Jammu and Kashmir until T-086)."

## Task
Add one risk row to `docs/RISKS_AND_LIMITATIONS.md` section 1 stating the limitation, with a measured count. No product, code, threshold or method change. The reassignment of the cells (T-086 proper) is after the presentation and is a separate task.

## Files
Modify: `docs/RISKS_AND_LIMITATIONS.md` only. Read: `data/products/cells.parquet`.

## Requirements
The count is measured on `cells.parquet` for the Lead's box (72.5 to 80.5 degrees E, 32.5 to 37.2 degrees N) by cell centre, labelled verified with its query; the row names the affected entities (India, Pakistan, China), what is unchanged (cells, harmonized values and verdicts per cell), and the fix (T-086).

## Git
Branch `docs/T-086-kashmir-limitation` from the latest `main`; first commit: this prompt; open a PR with the template; never merge; human identity, no AI attribution (D-020).
