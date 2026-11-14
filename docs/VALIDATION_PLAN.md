# Validation Plan: the Witness Stand

> **Validation status (method 0.1.0, 2026-11-15):** the tests of section 4 that have a status other than `NOT_RUN` actually ran; every one that did not run is `NOT_RUN`, and failures are recorded in section 5. The machine-readable results are in `data/products/validation_results.json`. Thresholds were **locked by the Project Lead at Gate G1 on 2026-11-14, before any results existed** (T-051, D-028). After that, any threshold change must be logged in `DECISION_LOG.md` with a reason, and the original threshold kept visible.

## 1. Principles

1. **Pre-registration:** criteria are fixed before results are seen.
2. **Compare against baselines:** every test compares (a) the naive raw combined record, (b) a single global ratio, and (c) our method.
3. **Publish failures:** results, including FAIL and INCONCLUSIVE, are shown in the app and recorded here.
4. **Sampled, not global:** passing these tests shows the method behaves correctly *where tested*. It does not establish global accuracy.

## 2. Validation cases (proposed, not yet verified against data)

| ID | Case | Fire regime / region | Era | Role |
|---|---|---|---|---|
| C1 | Indonesia, Sep–Oct 2015 | Tropical peat / Equatorial Asia | Clean overlap (pre-drift) | Survival; two eras |
| C2 | Brazilian Amazon, Aug 2019 | Tropical deforestation / S. Hemisphere S. America | Clean overlap | Survival |
| C3 | Pantanal, 2020 | Wetland / S. Hemisphere S. America | Clean overlap | Survival |
| C4 | SE Australia, Dec 2019–Jan 2020 | Temperate forest / Australia | Clean overlap | Survival; two eras |
| C5 | California, Aug–Sep 2020 | Mediterranean / Temperate N. America | Clean overlap | Survival |
| C6 | Siberia (Sakha/Yakutia), 2021 | Boreal / Boreal Asia | Overlap; drift onset to check | Survival; two eras |
| C7 | Canada, 2023 | Boreal / Boreal N. America | **Aqua drift era** | Stress test: are the intervals honest? |
| C8 | Southern African savanna (no event) | Savanna / S. Hemisphere Africa | Overlap | **Control:** no spurious anomalies at satellite-change dates |

These are well-documented extreme seasons. **Their detected anomaly magnitudes in our record are unknown until computed.** The Lead defines the exact bounding boxes and months by H6 (T-050).

### 2a. Case windows and boxes (T-050) **[APPROVED by the Lead 2026-11-14]**
Fixed before any result. Boxes are approximate rectangles (W, S, E, N in degrees) evaluated through `harmonize_area()` on the cells they contain; "peak window" is what test A1 compares.

| ID | Box (W, S, E, N) or entity | Analysis window | Peak window |
|---|---|---|---|
| C1 | Sumatra + Kalimantan: 95, −6, 119, 4 | 2015-06 to 2015-12 | 2015-09 to 2015-10 |
| C2 | Brazilian Amazon: −70, −12, −45, 0 | 2019-05 to 2019-11 | 2019-08 to 2019-09 |
| C3 | Pantanal: −59, −22, −54, −15 | 2020-06 to 2020-11 | 2020-08 to 2020-10 |
| C4 | SE Australia: 145, −39, 154, −28 | 2019-09 to 2020-03 | 2019-12 to 2020-01 |
| C5 | California: −124.5, 32.5, −114, 42 | 2020-06 to 2020-11 | 2020-08 to 2020-09 |
| C6 | Sakha/Yakutia: 105, 58, 150, 72 | 2021-05 to 2021-09 | 2021-07 to 2021-08 |
| C7 | Canada (entity `CAN`) | 2023-04 to 2023-10 | 2023-06 to 2023-07 |
| C8 | Southern African savanna (control): 20, −20, 35, −8 | 2011-01 to 2013-12 and 2017-04 to 2019-04 | Satellite-change dates 2012-01 and 2018-04 (±12 months) |

**Quiet months for test A2** (rule fixed now, not hand-picked): for each of C1, C4 and C6, the calendar month with the lowest baseline median in its box, in **2010** (pre-2012) and in **2023** (post-2022).


## 3. Tests and pass/fail criteria (PROPOSED; lock at G1)

| Test | What is measured | PASS criterion | Applies to |
|---|---|---|---|
| **A1. Real anomaly preserved (two independent paths)** | `pct_of_normal` computed from Aqua alone vs from converted S-NPP alone | Same direction (both above or both below normal); peak month within ±1; 90% intervals overlap. **Family pass:** ≥5 of 6 clean-overlap cases (C1–C6) | C1–C6 |
| **A2. Same fire, two eras** | Plant the event's real Aqua detections into a quiet pre-2012 month and its real VIIRS detections into a quiet post-2022 month; harmonize both | Harmonized peaks overlap within 90% intervals **and** the raw record shows a mismatch (otherwise the test is INCONCLUSIVE) | C1, C4, C6 |
| **B1. Satellite-change step removed** | Step ratio at 2012-01 and 2018-04: (series ÷ Aqua-only), 12 months after vs before | Raw: step clearly present. Harmonized: within ±10% of 1 in **≥80% of regions with sufficient data** | All fire regions |
| **B2. Planted sensor jump detected** | Multiply one witness by a random factor from a random date onward (≥50 trials) | Flagged (`WITNESS_DISAGREEMENT` or a widened interval) within 3 months in **≥90%** of trials; false flags in **<5%** of unplanted series | Random cells and regions |
| **B3. Known real artifacts surfaced** | Aqua/VIIRS ratio over time; S-NPP end 2026-11-02; outage dates | Drift visible as a ratio trend (reported with its onset estimate); outage months **100%** `CANNOT_DETERMINE` | Global |
| **C1. Cross-satellite agreement** | Converted S-NPP vs converted NOAA-20, region-months 2018–2021 | **≥85%** agree within combined 90% intervals | All fire regions |
| **D1. Uncertainty honest (coverage)** | Holdout 2017–2021: share of actual Aqua values inside the predicted 90% intervals | Between **80% and 97%** | All fire regions |
| **D2. Gaps and insufficiency** | Outage months; cells below the data thresholds | **100%** shown as `CANNOT_DETERMINE` / `NO_DETECTED_ACTIVITY`; report % of land cells with a determinable verdict | Global |
| **E1. Generalization (leave one region out)** | Fit without fire region *R*; predict R's 2017–2021 Aqua series | Our method beats the naive raw merge in **≥11 of 14** regions; all regions reported | All fire regions |
| **CTRL. Control** | Verdicts at satellite-change dates in C8 | No `ABOVE`/`BELOW` verdict at change dates that is absent from the Aqua-only series | C8 |
| **S1. Sensitivity** | Re-run A1 and B1 without the confidence filter, and with the Aqua-measured baseline (2003–2021) | Conclusions unchanged (report any that change) | C1–C6 |

## 4. Expected vs actual results

All results are for method 0.1.0 on the committed products, run 2026-11-14/15 (reports in `docs/validation/`, entries in `data/products/validation_results.json`). A status is `NOT_RUN` unless the test actually ran. No threshold was changed after a result.

| Test | Expected (hypothesis) | Actual | Status | Run date | Notes |
|---|---|---|---|---|---|
| A1 | Pass in most clean-overlap cases | 0 of 6 cases PASS: C1 and C2 INCONCLUSIVE, C3 to C6 FAIL (converted S-NPP-only is 58% to 80% of Aqua-only in the peak windows; the 90% intervals do not overlap) | **FAIL** | 2026-11-15 | Family result. C1 is officially INCONCLUSIVE (the D-028 S-NPP-only path has no baseline); C2 to C6 under D-029 (shared Aqua baseline). `docs/validation/T-020-results.md`, risk S19. |
| A2 | Raw shows a large post-2022 inflation; harmonized matches | — | NOT_RUN | — | Not run (T-023, assigned). |
| B1 | Raw steps at 2012 and 2018; harmonized flat | 2012-01: 14 of 14 regions within ±10% (0.955 to 1.007); 2018-04: 13 of 14 (0.952 to 1.104); raw steps 2.60 to 4.28 and 1.60 to 2.05 | PASS | 2026-11-15 | One region (MIDE, small) outside at 2018-04. `docs/validation/T-021-results.md`. |
| B2 | High detection rate | — | NOT_RUN | — | Not run (T-024, assigned). |
| B3 | Aqua drift visible after ~2021 | Drift visible as a ratio trend at night only (S-NPP onset 2024-05, NOAA-20 2024-09); 60 of 60 outage entity-months without estimate; 936 of 936 `CANNOT_DETERMINE` with `OUTAGE` | PASS | 2026-11-15 | PASS as written; the registered day-only drift method found none (T-021, section 4.1). |
| C1 | High agreement | — | NOT_RUN | — | Not run (T-024, assigned). |
| D1 | Coverage possibly below 90% (correlated errors) | Pooled 90% coverage 0.818 of 1,466 fire-region day/night units (50% interval 0.471) | PASS | 2026-11-15 | D1 read as the pooled share as defined; per-region and night shares reported separately (both below 80%): D1-REGIONS-EACH FAIL (7 of 14 regions inside), D1-NIGHT FAIL (0.750). Widening factor 1.262 reported, not applied. |
| D2 | 100% by construction | Estimate level: 0 violations in 70,906 entity-months; verdict level: 224,952 of 224,952 rows without an estimate are `CANNOT_DETERMINE` with `OUTAGE` (0 violations) | PASS | 2026-11-15 | Both halves ran. `docs/validation/T-022-results.md`. |
| E1 | Most regions beat naive | Our conversion beats the naive raw merge in 14 of 14 regions (threshold 11 of 14) | PASS | 2026-11-15 | A weak bar: the raw merge is the unconverted S-NPP count. A left-out region's 90% interval covers only 10% to 80% of its units (risk S18). `docs/validation/T-025-results.md`. |
| CTRL | No spurious verdicts | — | NOT_RUN | — | Not run (T-024, assigned). |
| S1 | Robust | — | NOT_RUN | 2026-11-15 | Overall S1 is NOT_RUN because half of it could not run (T-025b, assigned). The half that ran is its own entry: S1-BASELINE FAIL by the strict rule (12 of 13 peak-window verdicts unchanged, 1 changes). |

## 5. Failed tests

Every failure and every test that could not give a verdict, with what failed, by how much, the suspected cause and what claim we withdraw or narrow. Suspected causes are **hypotheses** unless marked verified.

- **A1, family FAIL (0 of 6; needed 5).** C3 Pantanal (S-NPP-only 192% against Aqua-only 253% of normal), C4 SE Australia (2,314% against 3,963%), C5 California (376% against 637%) and C6 Sakha (645% against 805%): the intervals do not overlap and the converted S-NPP estimate is 20% to 42% below Aqua in the peak windows. C1 (INCONCLUSIVE) and C2 (INCONCLUSIVE) had both paths within normal (94.6% and 86.1% of normal), so there was no anomaly to preserve. Direction and peak month agree in the failed cases, so the failure is a **bias of magnitude in extreme months**. T-020b confirmed by a pre-set rule that the Aqua/VIIRS ratio rises with activity (cell-day saturation is one hypothesis); a v0.2 activity factor (T-020c, D-030) moved the gaps by only 0.01 to 0.03 in log terms and did not meet the adoption rule, so v0.1 stays. **Claim withdrawn:** that the harmonized series preserves the **magnitude** of very large fire events; narrowed to: direction and timing are preserved, magnitude is under-stated by 20% to 40% in extreme months. Risk S19.
- **D1-NIGHT, FAIL (0.750).** Night intervals are too narrow. **Narrowed:** night-only intervals are not shown as 90% intervals; risk S16.
- **D1-REGIONS-EACH, FAIL (7 of 14 regions inside 80% to 97%).** The pooled PASS hides it. **Narrowed:** coverage is a property of the pooled collection, not of each region; per-region intervals can be too narrow.
- **S1-BASELINE, FAIL by the strict rule fixed in advance (1 of 13 peak-window verdicts of C1 to C6 changes when the Aqua-measured baseline replaces the harmonized baseline).** Overall S1 is `NOT_RUN` because the confidence-filter half could not run.
- **A1 C1 and C2, INCONCLUSIVE.** C1: under D-028 the S-NPP-only path has no baseline (at most 11 of the 20 baseline years). C2: both paths are within normal, so there is no anomaly to preserve. Neither counts as a PASS.
- **Not run:** A2 (T-023), B2, C1 and CTRL (T-024), and the confidence-filter half of S1 (T-025b) are assigned and are `NOT_RUN` here. No result is implied.

## 6. Limitations of this validation

- There is no ground truth: Aqua is used as the in-lifetime reference for 2012–2021, and Aqua itself has errors.
- Planted-jump tests share assumptions with the method (partly circular). Transplanting real events (A2) reduces, but does not remove, this.
- Validation is sampled across 8 cases and 14 regions. It is not cell-by-cell.
- The drift era (2022+) cannot be validated against a stable reference.
