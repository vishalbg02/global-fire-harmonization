# T-022 results: validation tests D1 (coverage) and D2 (gaps)

Run 2026-11-14/15 with `python pipeline/validation_d.py` on the final T-011/T-013 products (method `0.1.0-combined-no-baseline`). Code: `pipeline/validation_d.py` (reuses `pipeline/holdout.py` and `pipeline/harmonize.py`, unchanged); tests: `pipeline/tests/test_validation_d.py` (SYNTHETIC, answers known by hand). Entries in contract section 6 shape: `data/interim/qa/T-022_validation_entries.json` (not committed). Thresholds are the locked ones (D-028, `docs/VALIDATION_PLAN.md` section 3); none was changed.

## Summary

| Test | Status | Measured |
|---|---|---|
| D1 coverage, fire regions pooled (the locked criterion) | **PASS** | 0.818 of 1,466 D/N units |
| D2 estimate level (a part of D2) | **PASS** | 0 violations in 70,906 entity-months |
| D2 verdict level (the other part) | **PASS** | 936 of 936 rows without an estimate are `CANNOT_DETERMINE` with `OUTAGE`; 0 violations in 68,562 rows |
| D2 as a whole | **PASS** | both halves pass; 50.9% of entity-months and 67.8% of land cell-months have a determinable verdict |

## D1: are the 90% intervals honest

**Reading of the criterion [ASSUMPTION].** The plan says: share of actual Aqua values inside the predicted 90% intervals, between 80% and 97%, "applies to: all fire regions". I read it as one share, pooled over all fire-region units (the population is "all fire regions"; compare B1 and E1, which say "in at least 80% of regions" and "in 11 of 14 regions" when they mean per region). The status is decided on the pooled D/N units. This is the conservative reading only for the pooled number; the stricter per-region reading is run as its own entry and **fails**, see below. The Lead decided the pooled coverage passed the pre-registered rule, so no widening factor was applied.

**Pooled result [VERIFIED].** Fire-region-months 2017-2021, Aqua against converted S-NPP, units with at least 20 Aqua cell-days (same units as T-012).

| Set | Units | 90% interval | 50% interval | Status vs 80% to 97% |
|---|---|---|---|---|
| D/N units, all regions (**D1**) | 1,466 | **0.818** | 0.471 | **PASS** |
| Day | 830 | 0.870 | 0.516 | PASS |
| Night | 636 | 0.750 | 0.414 | FAIL (supplementary) |
| Day+night total | 636 | 0.847 | 0.497 | PASS |
| Countries, D/N units (supplementary) | 6,409 | 0.811 | 0.439 | PASS |
| Countries, total | 1,600 | 0.826 | 0.463 | PASS |

The numbers equal the T-012 report, as they should. The pooled 90% share is only 1.8 points above the lower bound.

**Per region, D/N units (supplementary, stricter reading) [VERIFIED].** The entry `D1-REGIONS-EACH` is **FAIL**: 7 of 14 regions with at least 30 units are inside 80% to 97%.

| Inside (PASS) | Coverage | Below 80% (FAIL) | Coverage |
|---|---|---|---|
| CEAM | 0.932 | AUST | 0.792 |
| EQAS | 0.813 | BOAS | 0.773 |
| NHAF | 0.855 | BONA | 0.733 |
| NHSA | 0.959 | CEAS | 0.704 |
| SEAS | 0.822 | EURO | 0.763 |
| SHAF | 0.805 | MIDE | 0.795 |
| SHSA | 0.900 | TENA | 0.794 |

UNASSIGNED (4 units) is not judged on its own. For region day+night totals also 7 of 14 are inside (outside: BONA, CEAM, EURO, MIDE, NHSA, SHAF, TENA). If the Lead or the plan intends the per-region reading, D1 is a FAIL, not a PASS.

**Widening factor, reported and not applied [VERIFIED].** The smallest `c` giving 90% on 2017-2018 is 1.262. Coverage on 2019-2021 is 0.811 unchanged and would be 0.877 with `c`.

**Known limits (risk S16).** Night units alone are below 80% (0.750). The 50% interval covers 0.471, below 50%: the intervals are slightly too narrow in the middle. Several size bands and about half of the regions and countries are below 80% (T-012 report).

**Not a clean out-of-sample test [VERIFIED as a property of the design].** `phi` and `kappa` were fitted on fit-period months, and the NOAA-20 pair used for them overlaps the holdout months on the Aqua side. Aqua and S-NPP are treated as independent in the interval, which they are not [ASSUMPTION, not quantified]. Aqua is the reference, not the truth.

## D2: gaps

**Estimate level [VERIFIED].** Run over every country, every fire region and the globe, every month with data (70,906 entity-months).
- 968 entity-months have no witness with a complete month in some day/night part: all 968 have no estimate.
- 5,082 entity-months have at least one partial witness; 0 estimates use a partial witness. As a second check, every incomplete witness row was made absurd (counts and variances times 1,000) in all 6,292 entity-months that have an incomplete row: **0** estimates, sds, witnesses or disagreement scales changed (5,324 with an estimate, 968 without).
- 0 months have no estimate although every part had a usable witness.
- "Usable" follows D-005: Aqua night does not count from 2024-05.

Status **PASS**. This covers the estimate half of the criterion only.

**Verdict level [VERIFIED].** Run on the T-014 products (PR #52, branch `origin/science/T-014-verdicts`, method with baselines and the `OUTAGE` code; products brought in uncommitted): `python pipeline/validation_d.py verdicts data/products/entity_month.parquet` (also reads `cell_month_harmonized.parquet` and `cells.parquet` from the same folder). Rules checked: a row without an estimate is `CANNOT_DETERMINE` with `OUTAGE`; `OUTAGE` never appears with an estimate; `INSUFFICIENT_BASELINE` and `WIDE_INTERVAL` rows are not determinable; `NO_DETECTED_ACTIVITY` has an estimate of 0. `NO_DETECTED_ACTIVITY` counts as an allowed outcome, as the plan text says.

| Table | Rows | Rows without estimate | Of these `CANNOT_DETERMINE` + `OUTAGE` | Violations |
|---|---|---|---|---|
| `entity_month` (countries 66,218, continents 2,051, globe 293) | 68,562 | 936 (904 country, 28 continent, 4 global; months 2002-07 to 2002-09 and 2026-11) | 936 | 0 |
| `cell_month_harmonized`, all cells | 16,477,734 | 224,952 | 224,952 | 0 |
| `cell_month_harmonized`, land cells | 16,206,123 | 221,244 | 221,244 | 0 |

Status **PASS**. Note: `entity_month` holds countries, continents and the globe, not the 14 fire regions, so the 968 no-estimate entity-months of the estimate-level run (which included regions) are 936 here; the extra 32 are region rows.

**Share of land cells with a determinable verdict [VERIFIED].** Land cells are the 55,311 cells with a `country_iso3` in `cells.parquet` (of 56,238). Determinable means any verdict but `CANNOT_DETERMINE`; "normal" means `ABOVE_NORMAL`, `BELOW_NORMAL` or `WITHIN_NORMAL`.

| Scope | Cell-months | Normal verdict | Not `CANNOT_DETERMINE` | Cells with at least one normal verdict | Cells with at least one determinable verdict |
|---|---|---|---|---|---|
| All cells | 16,477,734 | 2.9% | 68.3% | 21.4% | 99.8% |
| Land cells | 16,206,123 | 3.0% | 67.8% | 21.8% | 99.8% |
| Entity-months (countries, continents, globe) | 68,562 | 30.3% (ABOVE 6,119 + BELOW 6,318 + WITHIN 8,320 of 68,562) | 50.9% | | |

Reading it: most of the determinable cell-months are `NO_DETECTED_ACTIVITY` (10.8 million of 11.3 million); a normal-range verdict exists in only 3% of land cell-months (per calendar month between 0% and 6.4%), which is what D-028 anticipated for cells. Almost every cell has some determinable month (99.8%), but only about one in five ever gets a normal-range verdict. [VERIFIED as counts; the interpretation is mine.]

## Changes for the Lead [OPEN]
- `docs/VALIDATION_PLAN.md` section 4: D1 PASS (pooled), with the per-region FAIL and night limit recorded in section 5; D2 PASS (both halves) with the determinable shares above.
- Decide whether D1 means pooled (as read here) or per region; the plan text should say which.
