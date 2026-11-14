# T-022 results: validation tests D1 (coverage) and D2 (gaps)

Run 2026-11-14/15 with `python pipeline/validation_d.py` on the final T-011/T-013 products (method `0.1.0-combined-no-baseline`). Code: `pipeline/validation_d.py` (reuses `pipeline/holdout.py` and `pipeline/harmonize.py`, unchanged); tests: `pipeline/tests/test_validation_d.py` (SYNTHETIC, answers known by hand). Entries in contract section 6 shape: `data/interim/qa/T-022_validation_entries.json` (not committed). Thresholds are the locked ones (D-028, `docs/VALIDATION_PLAN.md` section 3); none was changed.

## Summary

| Test | Status | Measured |
|---|---|---|
| D1 coverage, fire regions pooled (the locked criterion) | **PASS** | 0.818 of 1,466 D/N units |
| D2 estimate level (a part of D2) | **PASS** | 0 violations in 70,906 entity-months |
| D2 verdict level (the other part) | **NOT_RUN** | needs T-014 |
| D2 as a whole | **NOT_RUN** until the verdict part runs | |

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

**Verdict level: NOT_RUN [OPEN].** "Outage months are 100% `CANNOT_DETERMINE` with `OUTAGE`" and the share of land cells with a determinable verdict need the T-014 table. `check_verdicts()` is written and tested on planted good and bad tables; it checks that rows without an estimate are `CANNOT_DETERMINE` with `OUTAGE`, that `OUTAGE` never appears with an estimate, that `INSUFFICIENT_BASELINE` and `WIDE_INTERVAL` rows are not determinable, that `NO_DETECTED_ACTIVITY` has an estimate of 0, and reports the determinable share. Note for T-014: the current `harmonize.records_from` does not emit `OUTAGE`; T-014 must add it, otherwise this test will fail.

After T-014 is merged and its products are built:

    python pipeline/validation_d.py verdicts data/products/entity_month.parquet

The result is written to `data/interim/qa/T-022_verdict_check.json`. The same function also accepts the cell-level table for the land-cell share. The "cells below the data thresholds" part of D2 is checked only through the `INSUFFICIENT_BASELINE` rule above.

## Changes for the Lead [OPEN]
- `docs/VALIDATION_PLAN.md` section 4: D1 PASS (pooled), with the per-region FAIL and night limit recorded in section 5; D2 stays NOT_RUN until the verdict part runs.
- Decide whether D1 means pooled (as read here) or per region; the plan text should say which.
