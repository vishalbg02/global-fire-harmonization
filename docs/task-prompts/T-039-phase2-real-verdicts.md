# Task prompt: T-039 phase 2, the real verdicts in the app

> Prepared for: Member 3 · Date: 2026-11-15 · Based on main @ cd4a532
> Source of truth: the Lead's comments on #38 and #46 ("T-039 phase 2 can start now: verdicts, % of normal, probabilities and reason codes from the real products; the raw-only note disappears per series"), docs/TASK_TRACKER.md row T-039 (all views on real products; stays open until this merges), and the Lead's status of 2026-11-15 ("T-039 phase 2 is the top priority, then T-044"). T-026 (number check by Member 2 and the Lead) depends on it. This prompt adds no scope beyond these.

## 1. Objective

Every view of the app runs on the real products (T-014, method 0.1.0, contract 0.1.1) and shows what they hold: verdicts, probabilities, % of normal, baselines, intervals and reason codes, for cells, countries, continents and the world, with nothing computed in the app and nothing mixed with fixtures. When this merges, the T-039 row can be closed and Member 2 and the Lead can run the T-026 number check on the app.

## 2. What I found on the real products today (2026-11-15, local API on data/products)

- The views already work on real verdicts without a change in raw-only logic (raw-only is decided per series; the products are no longer raw-only). Example, Indonesia 2015-09: estimate 19,068.7, 90% interval 17,320.2 to 20,817.2, 264.9% of normal, ABOVE_NORMAL with probability above 0.9999999, witnesses Aqua and S-NPP, S 1.0; the raw contribution lists Terra MODIS (raw only).
- `GET /api/validation` still holds no tests (`tests: []`), so the methods page says no test has been run yet (Member 2 integrates the results).
- **The anomaly list has many exact ties.** The API ranks by the larger of `p_above` and `p_below`. For 2015-09, 18 of the 35 listed areas have a score of 0.9999 or more; for 2023-08, 34 of 59; for 2026-10, 35 of 67. The order inside a tie is arbitrary, so the top of the list is not meaningful.
- `days_available` (partial months) is in `cell_month_witness` but in no served product, so the "partial-month indicator" the Lead approved on #39 cannot be shown (only the `OUTAGE` reason code reaches the app).

## 3. In scope

- A walk of every view on the real products (map verdict, activity and harmonized layers; calendar in % of normal and activity; evidence for cell, country, continent, world; satellite chart; anomaly list; CSV; methods page; offline copy) with every defect fixed or reported, and screenshots of the demo scenes (open question 4).
- The fixes the questions below lead to; an inventory of every number the app displays for T-026 (open question 5).
- Tests (SYNTHETIC data in test files) and the docs the changes touch.

## 4. Out of scope

- Changes in `pipeline/`, `data/` or the contract, unless the Lead decides so in a question below (the contract change would be Member 2's and the Lead's).
- T-044 (polygon area).

## 5. Open questions, with defaults

1. **Scope check.** The views already show the real verdicts, so phase 2 is mostly verification and the items below. Is there anything else you expect in phase 2? Default: no.
2. **Anomaly ties.** About half of each month's list has probability 1.0 to rounding, so the ranking cannot tell them apart. Default: keep the API's order (the app does not re-sort), and add a **secondary sort key in the API** only: after the larger probability, the larger distance from normal (`abs(log(pct_of_normal / 100))`, nulls last), then the entity id for a stable order; the rule is written in `api/README.md` and tested. Is a tie-break in the API acceptable, and is this the rule you want? (Alternative: a rule from Member 2.)
3. **Outage indicator (`days_available`).** No served product carries it. Options: (a) rely on the `OUTAGE` reason code, which the chart marks and the evidence panel already explain (no new data); (b) Member 2 adds the field to `entity_month` and `cell_month_harmonized` (a contract change, 0.1.2) and the app shows "partial month"; (c) the API reads `cell_month_witness` for the shown area (slow for large areas). Default: (a), and the partial-month indicator is dropped from the demo; say if you want (b).
4. **Demo scenes and screenshots.** Which views must be on real data for the merge and for T-061? Default: the validation cases of T-050 — Indonesia Sep to Oct 2015 (C1), Brazil Aug 2019 (C2), Canada 2023 (C7, the drift era), and the world for the latest month — each with the map verdict layer, the calendar, the evidence panel and the satellite chart, plus the anomaly list and the methods page.
5. **Number inventory for T-026.** Default: a table `docs/NUMBER_INVENTORY.md` (view, field, source product and column, format and rounding, unit), listing everything the app shows, so Member 2 and you can tick it off; the app computes nothing but formats stored values (whole percentages, one decimal for estimates). Is that the form you want, and is that the right place?
6. **How probabilities are shown.** The app shows whole percentages, so a probability of 0.9999999 reads "100%", which can look certain although the baseline's own uncertainty is not carried (a stated limitation). Default: show "more than 99%" for 0.995 or more and "less than 1%" for 0.005 or less, never 100% or 0%. Do you approve this wording? (It is display only; the stored value is unchanged.)
7. **Raw-only code.** The raw-only mode (banner, disabled controls, "Not available yet") is now dead on these products. Default: keep it as a guard (a products folder can still be swapped to a raw-only set), with its tests; remove nothing. Or remove it to simplify?

## 6. Acceptance

- Every view checked on the real products with screenshots; defects found are fixed or listed with their cause; no fixture data on screen.
- The decisions on questions 2 to 7 implemented and tested; lint, typecheck, tests and build pass; API tests pass if the API changed.
- The number inventory (or the reason it is not needed) is in the PR.
