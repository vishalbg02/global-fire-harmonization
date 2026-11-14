# Validation Plan: the Witness Stand

> **No validation test has been run yet.** Every status below is `NOT_RUN`. Thresholds are **PROPOSED** and must be **locked by the Project Lead at Gate G1, before any results exist** (T-051). After that, any threshold change must be logged in `DECISION_LOG.md` with a reason, and the original threshold kept visible.

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

| Test | Expected (hypothesis) | Actual | Status | Run date | Notes |
|---|---|---|---|---|---|
| A1 | Pass in most clean-overlap cases | — | NOT_RUN | — | |
| A2 | Raw shows a large post-2022 inflation; harmonized matches | — | NOT_RUN | — | |
| B1 | Raw steps at 2012 and 2018; harmonized flat | — | NOT_RUN | — | |
| B2 | High detection rate | — | NOT_RUN | — | |
| B3 | Aqua drift visible after ~2021 | — | NOT_RUN | — | |
| C1 | High agreement | — | NOT_RUN | — | |
| D1 | Coverage possibly below 90% (correlated errors) | — | NOT_RUN | — | |
| D2 | 100% by construction | — | NOT_RUN | — | |
| E1 | Most regions beat naive | — | NOT_RUN | — | |
| CTRL | No spurious verdicts | — | NOT_RUN | — | |
| S1 | Robust | — | NOT_RUN | — | |

## 5. Failed tests

*None recorded. No tests have run.* When a test fails, record what failed, by how much, the suspected cause, and what claim we withdraw or narrow.

## 6. Limitations of this validation

- There is no ground truth: Aqua is used as the in-lifetime reference for 2012–2021, and Aqua itself has errors.
- Planted-jump tests share assumptions with the method (partly circular). Transplanting real events (A2) reduces, but does not remove, this.
- Validation is sampled across 8 cases and 14 regions. It is not cell-by-cell.
- The drift era (2022+) cannot be validated against a stable reference.
