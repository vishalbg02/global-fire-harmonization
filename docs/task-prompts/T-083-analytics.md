# Task prompt: T-083 Analytics panel

> Prepared for: Member 2 · Date: 2026-11-15 · Based on `content/T-076-plain-language` (PR #77, for `app/src/content/sources.ts`) on top of main
> Source of truth: the Lead's comment on PR #74 ("New from the Lead: best analytics (T-083)").

## 1. Project context
The users are emergency managers (is this month abnormal here?), land managers (is the regime changing?), scientists and journalists (did burning change, or did the observation change?). The analytics must serve that question from the stored values only.

## 2. Task objective
A self-contained component `AnalyticsPanel` in `app/src/components/analytics/` that Member 3 mounts as a tab of the T-070 card, with five views: (1) raw versus harmonized by year with the satellite joins marked (2012-01 S-NPP, 2018-04 NOAA-20); (2) the season profile: the normal band (p25 to p75) of each calendar month, the median and the selected year's line; (3) the rank "Nth highest <month> of the record" from the stored estimates, with ties and missing years stated; (4) coverage: the share of the area's cells with a determinable verdict this month; (5) compare: a second area overlaid in % of normal.

## 3. Assigned responsibility
T-083 / P0 · Owner: Member 2 (component), Member 3 mounts it (props agreed on PR #78) · Reviewer and merger: Member 1.

## 4. Relevant files and directories
- Create: `app/src/components/analytics/*` (pure computations, chart options, component, styles, tests), `pipeline/analytics_check.py` and `pipeline/tests/test_analytics_check.py` (an independent recomputation from `entity_month.parquet`, compared with the component's own functions run in Node)
- Read: `app/src/api/client.ts`, `contract.ts`, `app/src/content/sources.ts`, `app/src/components/witness/chartOption.ts` (colours), `docs/PROJECT_PLAN.md` §5
- Do not touch other app files.

## 5. Approved technologies
React, TypeScript strict, ECharts (already used), vitest. No new dependency.

## 6. Architecture and data contract
Data only through the existing API client (`fetchSeries`, `fetchMapCells`, `fetchMeta`); nothing is computed on the server; no contract change. Fixtures only in tests, labelled SYNTHETIC.

## 7. Inputs
`GET /api/series`, `GET /api/map` (cells of the month, optionally passed in by the parent from its cache), `GET /api/meta`.

## 8. Expected outputs
The component, its tests, the cross-check, screenshots at 1440x900 and 375 from the real API on the real products.

## 9. Implementation requirements
1. **No new statistic:** no trend line, regression or forecast. Only sums of stored values, percentiles already stored (baseline p25, p50, p75), ranks and shares. Annual sums are labelled "sum of monthly estimates; intervals not combined" and cover only the months that have an estimate; a partial year is marked.
2. **Rank:** competition ranking over the years that have an estimate for that calendar month; equal estimates share a rank and are stated; years with no estimate are listed; a provisional selected month says so.
3. **Coverage:** cells whose centre lies inside the area's bounding box (the API's own custom-area rule, edges inclusive), counted by verdict; determinable means any verdict except `CANNOT_DETERMINE`. **Limit, stated in the component:** for a country or a continent the bounding box can include cells of neighbouring areas (the map cells carry no country field); the global figure is exact.
4. Every chart: unit, a source line built from `sources.ts` and `DATA_SOURCES.md` links, labels, a table alternative inside `details`, and an `aria-label`.
5. Real data only: no sample numbers in production code.
6. Design: the brief on PR #73: the existing chart colours, tabular figures, thin rules, no gradients, no emoji, no marketing words.

## 10. Constraints: do not modify
Method, thresholds, products, the API, other components.

## 11. Acceptance criteria
Each of the five views shows real values for a preset area; a test recomputes the numbers from the products for two areas and they agree; screenshots attached; `npm test`, typecheck, lint, `ruff` pass.

## 12. Required tests
`npm test` (pure computations on SYNTHETIC values, chart options, rendering with a mocked client); `python -m pytest pipeline/tests/test_analytics_check.py -q` (recomputation from the real products, skipped without them).

## 13. Documentation updates
The PR description (props, limits). The T-083 tracker row is in PR #74.

## 14. Git branch and PR instructions
Branch `frontend/T-083-analytics` from `content/T-076-plain-language` (it holds `sources.ts`; the PR notes the dependency on PR #77). First commit: this prompt. Open a PR with the template; never merge; human identity (D-020).

## 15. Out-of-scope or blocking issues
Mounting the panel as a tab and the exact props (T-070, Member 3, PR #78). An exact coverage for countries needs the cell-to-country link in the map payload (API, Member 3).
