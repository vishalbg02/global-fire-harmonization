# Task prompt: T-092 "World" everywhere (the area name of the global series)

> Prepared for: Member 2 · Date: 2026-11-15 · Based on main (HEAD at branch creation)
> Source of truth: the Lead's comment on PR #97: "Label decision: **World everywhere** (T-092, Member 2). The Lead signs off T-078 and merges this PR after T-092 lands."

## Task
The global series is called "World" on the summary card but "Global" in the stored name (`entity_month.entity_name` for `GLOBAL`), the story chip, the story headline and `featured.ts`. Use **"World"** everywhere the area is named. The stored name is a product value: only the name of the 293 `GLOBAL` rows changes, no number and no verdict.

## Files
- `pipeline/verdicts.py`, `pipeline/raw_only.py` (the name written for `GLOBAL`), `data/products/entity_month.parquet` (LFS; rewrite only `entity_name` of the `GLOBAL` rows, every other value and the schema unchanged, verified), `pipeline/featured_stories.py` output (`app/src/content/featured.ts`, `docs/validation/T-079-featured-stories.md`, regenerated), `app/src/components/analytics/AnalyticsPanel.tsx` (the name used when the link carries only the id) and its test, `docs/DATA_SOURCES.md` (a note), `docs/validation/` report of the checks.
- Not changed: entity ids (`GLOBAL`), verdicts, numbers, thresholds, method, the wordmark "Global Fire Harmonization" (the project name), the generic wording of the aria labels ("Global anomalies", "Global fire activity map").

## Requirements
Every other column of `entity_month` equal to `main` (compared value by value, 68,562 rows); `contract_check` on the small tables; `number_check.py`, `featured_stories.py --check`, `analytics_check.py` 0 mismatches; app and pipeline tests; products via Git LFS with SHA-256 in the PR.

## Git
Branch `frontend/T-092-world-label` from the latest `main`; first commit: this prompt; PR with the template and the real-data statement; never merge; human identity, no AI attribution (D-020).
