/**
 * Static content of the "Methods and validation" page (T-041).
 *
 * Where each block comes from (the Lead approves the wording before release):
 * - METHOD_SECTIONS: docs/SCIENTIFIC_METHODOLOGY.md (label 0.1.0-proposed, partly outdated), docs/DECISION_LOG.md,
 *   docs/DATA_SOURCES.md, docs/DATA_CONTRACT.md, docs/RISKS_AND_LIMITATIONS.md and the docstring of
 *   pipeline/harmonize.py. Each section names its source. Status labels are kept as the sources give them.
 * - GRID_EVIDENCE: the four rows of the D-009 table in docs/DECISION_LOG.md, unchanged.
 * - PLANNED_TESTS and VALIDATION_CASES: docs/VALIDATION_PLAN.md sections 2 and 3, pass rules as written there.
 *   They are plans. No test result and no status is stored here.
 * - REFERENCES: docs/SCIENTIFIC_METHODOLOGY.md section 9, as written.
 * - DATASET_DOIS: SP_DOIS and NRT_DOIS in api/fire_api/export.py, copied exactly.
 *
 * Nothing here is computed. The baseline, probabilities and verdicts are those of the T-014 products (D-028).
 */

export type Label = 'APPROVED' | 'PROPOSED' | 'VERIFIED' | 'LIMITATION' | 'OPEN' | 'NOT_BUILT_YET'

export interface MethodSection {
  id: string
  title: string
  paragraphs: readonly string[]
  labels: readonly Label[]
  source: string
}

export const METHOD_SECTIONS: readonly MethodSection[] = [
  {
    id: 'hotspot',
    title: 'What a hotspot is, and what it is not',
    paragraphs: [
      'A hotspot is the centre of a satellite pixel flagged as containing one or more active fires at overpass time. The fire is usually much smaller than the pixel.',
      'A hotspot is not a fire, a fire count, a perimeter or burned area. Several hotspots can come from one fire. One hotspot can contain several fires.',
      'No hotspot does not mean no fire. Clouds, heavy smoke, canopy, data gaps, and fires that start and end between overpasses all produce silence. FIRMS points carry no cloud or missing-data information.',
      'Polar-orbiting satellites take snapshots, a few per day. They do not watch continuously.',
      'This app therefore calls its quantity "satellite-detected fire activity", counted in fire-active cell-days. It never says "number of fires".',
    ],
    labels: ['VERIFIED'],
    source: 'docs/SCIENTIFIC_METHODOLOGY.md, section 1',
  },
  {
    id: 'why-not-add',
    title: 'Why MODIS and VIIRS cannot simply be added together',
    paragraphs: [
      'MODIS pixels are about 1 km at nadir and grow strongly toward the swath edge. VIIRS (375 m) pixels are 375 m. VIIRS splits one fire into more points.',
      'VIIRS is much more sensitive to small fires. Schroeder et al. (2014) report about 3 times more fire pixels by day and about 25 times at night, against the 750 m baseline.',
      'The confidence scales differ: MODIS uses 0 to 100, VIIRS uses the classes l, n and h. The satellites also pass at different local times: Terra about 10:30 and 22:30, Aqua about 13:30 and 01:30, S-NPP about 13:30, NOAA-20 and NOAA-21 about 12:40.',
      "MODIS orbits are drifting because the satellites' fuel is exhausted. The time of day Aqua samples changes late in its life.",
      'Adding everything together creates artificial jumps: in January 2012 when VIIRS arrives, in 2018 when NOAA-20 is added, in 2024 when NOAA-21 is added, in November 2026 when S-NPP ends, and gradually during the drift years.',
      'The ratio of VIIRS to MODIS detections varies by region and fire regime, because small fires are where MODIS misses most. A single global conversion factor is therefore not valid.',
      'The raw combined record in this app does add the satellites. It shows the sensor jumps. It must not be read as fire activity.',
    ],
    labels: ['VERIFIED', 'LIMITATION'],
    source: 'docs/SCIENTIFIC_METHODOLOGY.md, section 2; docs/DATA_SOURCES.md, "Gridding (T-006)" and "Raw-only products (T-014a)"',
  },
  {
    id: 'witnesses',
    title: 'The witnesses and what each does',
    paragraphs: [
      'Each satellite sensor is called a witness. Each one reports what it saw. None is treated as the truth.',
      'Aqua MODIS (record from July 2002): the display scale. Values are expressed on the Aqua-equivalent scale. Aqua enters the combination with a ratio of 1 and no ratio uncertainty. Aqua night is excluded from the combination from 2024-05 on; Aqua day stays (D-005, APPROVED; see the Aqua drift section).',
      'S-NPP VIIRS (20 January 2012 to 2 November 2026): converted to the Aqua-equivalent scale and combined.',
      'NOAA-20 VIIRS (from 1 April 2018, ongoing): converted to the Aqua-equivalent scale and combined.',
      'Terra MODIS (D-006, PROPOSED): shown in the raw view only. It never enters the harmonized estimate, because Terra samples the morning and would need a second calibration chain.',
      'NOAA-21 VIIRS (D-007, PROPOSED): excluded from the first version. It is not in the yearly archives, and NOAA-20 already covers the present.',
      'The harmonized record starts in 2002-07 (D-006, PROPOSED).',
      'The end dates of the Aqua and Terra missions are not known from FIRMS data.',
    ],
    labels: ['APPROVED', 'PROPOSED', 'VERIFIED', 'OPEN'],
    source:
      'docs/DECISION_LOG.md, D-005, D-006, D-007; docs/DATA_SOURCES.md, section 4 "Satellite record dates"; docs/SCIENTIFIC_METHODOLOGY.md, sections 3 and 4.4',
  },
  {
    id: 'grid',
    title: 'The grid',
    paragraphs: [
      'APPROVED (D-009, 2026-11-14): a regular latitude and longitude grid. The analysis grid is 0.5 degrees. The fine cell-day grid is 0.05 degrees. A fine cell belongs to the analysis cell that holds its centre.',
      'A detection marks its fine cell as fire-active for that UTC day, per witness and per day or night. This removes multiple points per fire and same-day duplicates. The unit is the fire-active cell-day.',
      'The sizes were chosen at Gate G1 by a rule fixed beforehand: best Aqua versus S-NPP agreement on 2012 to 2016, measured before any validation. The four candidates and their scores are in the table on this page.',
      'Known consequences (from the decision log): Aqua night activity is thin, so night strata rely on pooling. Cell-level verdicts will often be "cannot determine"; country and continent are the main verdict levels.',
    ],
    labels: ['APPROVED', 'VERIFIED', 'LIMITATION'],
    source: 'docs/DECISION_LOG.md, D-009; docs/SCIENTIFIC_METHODOLOGY.md, section 4.2; docs/DATA_SOURCES.md, "Gridding (T-006)"',
  },
  {
    id: 'filters-masks',
    title: 'Filters and masks',
    paragraphs: [
      'Kept detections: type 0 (presumed vegetation fire) for standard-product rows; MODIS confidence 30 or more; VIIRS confidence n or h. Near-real-time rows have no type.',
      'A static-source mask removes cells dominated by non-vegetation sources. It applies to every row of every year, so there is no artificial step where standard data hand over to near-real-time data in 2026 (approved by the Lead, 2026-11-14).',
      'APPROVED (D-025, 2026-11-14): persistent night sources join the static mask. They are gas flares, industrial heat and volcanoes. A 0.05 degree fine cell is added when its kept VIIRS night detections, 2012 to 2025, meet all four conditions: lit on at least 1% of nights; in at least 10 of the 12 calendar months; with at least half of those nights outside its 3 busiest calendar months; and with day detections on at most 0.5 times as many days as nights.',
      'The fourth condition exists because a flare burns around the clock while a vegetation fire mostly burns in the afternoon. It keeps the Chiquitano dry forest in Bolivia out of the mask.',
      'The mask applies to every witness, day and night, in all years.',
      'APPROVED (D-025): one-off events get no local weight in calibration. If a single month holds more than 50% of a stratum\'s overlap cell-days, the stratum uses its region\'s ratio. This is a general rule, not a volcano list.',
      'LIMITATION (accepted by the Lead, 2026-11-14): the mask misses flares lit on fewer than 1% of nights or in fewer than 10 months. Eight Bolivian cells are still flagged and their cause is OPEN. The Fagradalsfjall NOAA-20 June to August night ratio is still treated as local.',
      'A sensitivity run without the confidence filter is part of the validation plan (test S1).',
    ],
    labels: ['APPROVED', 'LIMITATION', 'OPEN'],
    source:
      'docs/DECISION_LOG.md, D-025; docs/DATA_SOURCES.md, "Gridding (T-006)" and "Persistent night-source mask (D-025)"; docs/RISKS_AND_LIMITATIONS.md, S11 to S15; docs/SCIENTIFIC_METHODOLOGY.md, section 4.1',
  },
  {
    id: 'calibration',
    title: 'Calibration to the Aqua-equivalent scale',
    paragraphs: [
      'Each VIIRS witness is converted to the Aqua scale with a ratio. The ratio is the sum of Aqua cell-days divided by the sum of the witness cell-days over the months when both were operating. It is fitted separately for each stratum, for day and night, and for each season (DJF, MAM, JJA, SON).',
      'A stratum is a 2.5 degree block inside a GFED fire region. The fit periods are 2012-01 to 2016-12 for S-NPP and 2018-04 to 2021-12 for NOAA-20. The years 2017 to 2021 are held out for S-NPP.',
      'Partial pooling: a stratum with little data borrows from its fire region, and the region borrows from the global ratio, in proportion to how little data it has. The field pooling_level (LOCAL, REGION or GLOBAL) records which level dominates. A stratum keeps a local weight only with at least 3 overlap months.',
      'The uncertainty of each ratio comes from a block bootstrap over months (1,000 replicates), which keeps within-month dependence.',
      'Measured global ratios show why one factor does not fit: by day a VIIRS witness records about 3 to 4 times the Aqua cell-days. By night it records about 13 to 25 times.',
      'Calibration is fitted only on the overlap years and is never re-fitted per year. Per-year re-fitting would absorb real changes.',
      'LIMITATION: the ratios assume that the fire-size mix inside a stratum stays the same. If fires get systematically smaller or larger, the ratio drifts. This is not corrected.',
      'OPEN: the low night ratios in savanna and agricultural fire regions are a hypothesis, not a verified fact. The idea is that VIIRS sees many small night fires that MODIS misses. Validation test E1 is to check it. The holdout evaluation (T-012) is reported in its own section below.',
    ],
    labels: ['VERIFIED', 'APPROVED', 'LIMITATION', 'OPEN'],
    source:
      'docs/DATA_SOURCES.md, "Calibration (T-011)"; docs/SCIENTIFIC_METHODOLOGY.md, sections 4.3 and 5; docs/RISKS_AND_LIMITATIONS.md, S2 and S15',
  },
  {
    id: 'combining',
    title: 'Combining the witnesses, and the uncertainty',
    paragraphs: [
      'Status of this step: built as pipeline/harmonize.py. The method version of harmonize_area() is 0.1.0-combined-no-baseline. It was approved by the Lead on 2026-11-14 (PR #43). The harmonized products (T-014) have method version 0.1.0.',
      'For an area and a month, each witness gives an Aqua-equivalent estimate: the ratio times its cell-days, summed over strata, separately for day and for night. Raw cell-days are summed per witness and stratum before they are converted.',
      'For each month the witnesses are combined with a precision-weighted mean separately for day and for night, and the two combined estimates are added. The disagreement factor S is computed over both parts together. The variances of the two parts add. A witness with a smaller variance counts for more. Only witnesses with every day of the month available count. If none counts, there is no estimate.',
      'The variance of each witness has two parts. First, counting noise: an overdispersion factor (phi) times the count, plus a term that grows with the square of the size of the estimate (kappa times the estimate squared). Second, ratio error, which is shared: strata that use the same ratio share the same error, so these errors are added fully correlated.',
      'Phi and kappa were estimated once, on the calibration fit periods only. By day phi is 2.25 and kappa is 0.0084. By night phi is 2.47 and kappa is 0.0164. They apply to every witness. They are lower bounds, because the ratios were fitted on the same months.',
      'Disagreement inflation: if the witnesses disagree more than their variances allow, the combined standard deviation is multiplied by S = sqrt(chi-squared / (N - 1)). This is applied only when S is above 1. The reason code WITNESS_DISAGREEMENT is given only when S is above 2 (the Lead\'s decision).',
      'The interval is a 90% normal interval, with the lower bound at 0. A zero count has a variance floor of one cell-day.',
      'For any area, raw cell-days are summed per witness and stratum first, then converted. Per-cell intervals are never added, because the ratio error is shared. One function, harmonize_area(), does this for both the batch products and the custom-area API.',
      'No estimate is made for 2002-07 to 2002-09 (Aqua outage days) or for a partial month.',
      'LIMITATION: strata that share no ratio source are treated as independent. The region estimates share the global one, so the interval of a very large area can still be too narrow. The witnesses see the same fires, so intervals may be optimistic. The phi and kappa fit is not perfect in every size band.',
      'Whether the interval width is right is test D1 (coverage on the 2017 to 2021 holdout). It has not been run.',
    ],
    labels: ['APPROVED', 'VERIFIED', 'LIMITATION'],
    source:
      'pipeline/harmonize.py, module docstring; docs/DATA_SOURCES.md, "Combining the witnesses and harmonize_area() (T-013)"; docs/SCIENTIFIC_METHODOLOGY.md, sections 4.4 and 4.5',
  },
  {
    id: 'aqua-drift',
    title: 'The Aqua drift and the cutoff',
    paragraphs: [
      "Aqua's orbit is drifting because its fuel is exhausted. The time of day it samples is changing (LAADS).",
      'APPROVED (D-005, the Lead, 2026-11-14), as a documented deviation from the registered rule: Aqua night is excluded from the combination from 2024-05 on. Aqua day stays. Day and night are combined separately in every month and then added. The months from 2024-05 carry the reason code AQUA_DRIFT_ERA.',
      'VERIFIED (T-012): the registered test used the global day series of S-NPP only. It found no drift (onset 2025-06 at the edge of the range, slope -5.4% per year, the flat model better by 6.1 BIC). It missed a drift visible only at night. Night drift was detected in S-NPP with onset 2024-05 (interval 2022-10 to 2025-04, -12.0% per year, delta BIC +28.9) and in NOAA-20 with onset 2024-09 (interval 2024-03 to 2025-02, -19.0% per year, delta BIC +50.7). The earlier onset, 2024-05, is used as the conservative choice. Values are expressed on the Aqua-equivalent scale as a display scale, not as truth.',
      'LIMITATION: the cutoff date was chosen after seeing the results, because the registered primary series did not give it. It is therefore not a registered result. The choice of 2024-05 rests on the earlier of two overlapping onset intervals.',
      'OPEN: the cause of the drift (a change in Aqua, in its processing, or in VIIRS) is not known. The diagnostic cannot separate them.',
      'LIMITATION: the drift era (2022 onward) cannot be validated against a stable reference. Test B3 shows the drift as a ratio trend and reports its onset estimate. It has not been run.',
    ],
    labels: ['APPROVED', 'VERIFIED', 'LIMITATION', 'OPEN'],
    source:
      'docs/DECISION_LOG.md, D-005; docs/DATA_SOURCES.md, "Aqua drift diagnostic (T-012)" and "Combining the witnesses" (AQUA_FROM); docs/SCIENTIFIC_METHODOLOGY.md, section 3; docs/VALIDATION_PLAN.md, sections 3 and 6',
  },
  {
    id: 'holdout-evaluation',
    title: 'Holdout evaluation (T-012), measured',
    paragraphs: [
      'This is the holdout evaluation (T-012). It is not the recorded validation test D1, which stays "not run". The two are different checks and this one does not replace D1.',
      'VERIFIED: the question is how well the converted S-NPP estimate predicts what Aqua counted in 2017 to 2021, months not used to fit the ratios. Units are fire-region-months and country-months, day and night separately, and the day+night total. A unit needs at least 20 Aqua cell-days. The actual value is the Aqua cell-day count, which is itself an estimate and not ground truth.',
      'Median absolute log error (ours / naive raw merge / one global ratio), regions: day 0.090 / 1.347 / 0.265; night 0.209 / 2.979 / 0.447; day+night 0.086 / 1.526 / 0.224. Countries: day 0.149 / 1.434 / 0.316; night 0.224 / 2.949 / 0.569; day+night 0.100 / 1.439 / 0.213. Ours has a lower pooled error than both in every one of these rows.',
      'VERIFIED: where ours does not win (groups with at least 30 units). Regions: EURO day (ours 0.146, global ratio 0.134) and EURO night (0.281 against 0.223). Countries, all against the global ratio: ESP day (0.177 vs 0.153), KAZ night (0.490 vs 0.383), PRY day (0.104 vs 0.103), SDN day (0.173 vs 0.142), SDN night (0.168 vs 0.136), URY day (0.208 vs 0.184), MLI day+night (0.080 vs 0.076), SDN day+night (0.108 vs 0.088). The raw merge never beats ours.',
      'VERIFIED: coverage of the 90% interval (target 80% to 97%). Units, day and night together: 0.818 for regions (1,466 units) and 0.811 for countries (6,409 units). Day+night totals: 0.847 for regions and 0.826 for countries.',
      'LIMITATION: night units are below 80%: 0.750 for regions (636 units) and 0.794 for countries (1,611 units). Roughly half of the individual regions and countries also fall below 80%: 7 of 14 region groups and 45 of 87 countries for day and night units. The 50% interval covers 0.471 (regions) and 0.439 (countries), so the intervals are slightly too narrow in the middle as well.',
      'LIMITATION: Aqua and S-NPP see many of the same fires, so the two sides are not independent, and the interval ignores their covariance. The variance model was partly fitted on months that overlap this holdout (Aqua against NOAA-20), so the coverage is not a clean out-of-sample test. Aqua is the reference here but has errors and drift too. Agreement with Aqua is not agreement with the truth.',
      'OPEN: test D1, the independent coverage check, has not been run.',
    ],
    labels: ['VERIFIED', 'LIMITATION', 'OPEN'],
    source:
      'docs/DATA_SOURCES.md, "Holdout evaluation 2017 to 2021 (T-012)" (tables "Main result", "Where ours does not beat a baseline", "Coverage of the 90% interval", "Coverage check asked by the Lead on PR #43" and "Reading it correctly")',
  },
  {
    id: 'baseline-verdicts',
    title: 'The baseline and the five verdicts',
    paragraphs: [
      'APPROVED (D-028, 2026-11-14): the baseline is the same calendar month over 2003 to 2022, taken from the harmonized estimates of the years that have one. Its 25th, 50th and 75th percentiles (empirical, linear interpolation) define the normal range. With fewer than 15 of the 20 years there is no baseline. Sensitivity test S1 repeats the check with an Aqua-measured baseline (2003 to 2021).',
      'The estimate is treated as a normal distribution with the estimate as mean and its standard deviation, cut at 0. The probability above the 75th percentile, below the 25th and between them are computed from it.',
      'The verdict follows in this order: no estimate (an outage): cannot determine, reason OUTAGE; fewer than 15 baseline years: cannot determine, INSUFFICIENT_BASELINE; an estimate of 0, no detection by any witness and a baseline 75th percentile of 1 cell-day or less: NO_DETECTED_ACTIVITY (never shown as below normal); a baseline median below 5 Aqua-equivalent cell-days: cannot determine, INSUFFICIENT_BASELINE; then ABOVE_NORMAL, BELOW_NORMAL or WITHIN_NORMAL when the probability is at least 0.8; otherwise cannot determine, WIDE_INTERVAL.',
      'ABOVE_NORMAL means the estimate is above the baseline\'s 75th percentile with at least 80% probability. It does not mean an anomaly: about half of all months lie outside the middle half of their baseline by construction. BELOW_NORMAL is the same below the 25th percentile, and WITHIN_NORMAL is at least 80% probability of lying between the two.',
      'CANNOT_DETERMINE means the data cannot support a verdict; it does not mean normal. The reason codes say which case it is. NO_DETECTED_ACTIVITY means no detections and a baseline that is also near zero.',
      'Caveat codes never change a verdict: PROVISIONAL_NRT, SINGLE_WITNESS, WITNESS_DISAGREEMENT (S above 2), AQUA_DRIFT_ERA, POOLED_CALIBRATION (more than half of the converted cell-days use a region or global ratio) and DIURNAL_CAVEAT (India and Punjab and Haryana, October and November, from 2020).',
      'VERIFIED (measured on the T-014 products, 293 months, 2002-07 to 2026-11): the share of months that can be judged as above, below or within normal is 29.6% for countries, 52.7% for continents, 34.1% for the world and 2.9% for grid cells. 65% of cell-months have no detected activity. 189 of the 293 world months are CANNOT_DETERMINE with WIDE_INTERVAL.',
      'HYPOTHESIS, not investigated: the world\'s baseline range is narrow against the roughly 6% relative error of the estimate, so the probability of lying within it often stays below 0.8.',
      'LIMITATION: the uncertainty of the baseline percentiles is not carried into these probabilities.',
      'Nothing is ever interpolated or filled. Missing data stays missing.',
    ],
    labels: ['APPROVED', 'VERIFIED', 'LIMITATION'],
    source:
      'docs/DECISION_LOG.md, D-028; docs/DATA_SOURCES.md, "Baseline, probabilities, verdicts and the real harmonized products (T-014)"; docs/DATA_CONTRACT.md, enumerations',
  },
  {
    id: 'custom-areas',
    title: 'Custom areas and grid cells',
    paragraphs: [
      'A custom area is a rectangle drawn on the map. It is approximated by the 0.5 degree grid cells that make it up. Its edges are therefore not exact.',
      'The same method is used as for countries and continents: raw cell-days are summed per witness and stratum, then converted, then combined. Cell intervals are not added up.',
      'A country is assigned to a cell by the country with the most detections in that cell. Cells with no country count in the global total only.',
      'LIMITATION: custom areas are approximated by grid cells.',
    ],
    labels: ['LIMITATION', 'VERIFIED'],
    source:
      'docs/SCIENTIFIC_METHODOLOGY.md, sections 4.5 and 8; docs/DATA_CONTRACT.md, section 1 and the 0.1.1 additions; docs/DATA_SOURCES.md, "Gridding (T-006)"',
  },
  {
    id: 'raw-only',
    title: 'Raw-only data and NOT_HARMONIZED',
    paragraphs: [
      'APPROVED (D-026, 2026-11-14): while harmonization was not available, the products showed raw satellite data only. Every harmonized field is empty, no witness is listed as used, the verdict is CANNOT_DETERMINE and the reason code is NOT_HARMONIZED.',
      'The text shown to users is: "Harmonized values aren\'t computed yet; this shows raw satellite data only."',
      'The raw combined number adds satellites that see the same fires: Aqua, Terra and VIIRS. It is not comparable across years and is not a measure of fire activity.',
      'The raw-only products were replaced by the harmonized products (T-014). This section describes the earlier state (D-026) and the NOT_HARMONIZED code, which no longer appears in the products.',
    ],
    labels: ['APPROVED', 'VERIFIED'],
    source:
      'docs/DECISION_LOG.md, D-026; docs/DATA_CONTRACT.md, 0.1.1 additions; docs/DATA_SOURCES.md, "Raw-only products for the app (T-014a)"',
  },
  {
    id: 'limitations',
    title: 'Limitations',
    paragraphs: [
      'Hotspots are not burned area, emissions or fire counts.',
      'No correction for regional shifts in burning time relative to the overpass. Example reported by others: Punjab and Haryana burning moved later in the day between 2020 and 2024. Such areas carry the reason code DIURNAL_CAVEAT where documented, and the app never claims burning fell there.',
      'Ratios assume the fire-size mix within a stratum stays the same.',
      'Intervals may be too narrow, because the witnesses see the same fires and their errors are partly correlated.',
      'Uncertainty of the baseline is not carried forward.',
      'Per-cell overpass counts and cloud cover are not modelled. Ratios fitted locally absorb some of the effect of overpass frequency.',
      'Custom areas are approximated by grid cells.',
      'Validation is sampled, not global. No claim of global accuracy is made. There is no ground truth: Aqua is the reference for 2012 to 2021, and Aqua has errors too.',
      'OPEN: MODIS version strings differ across years (6.2, 6.03 and 61.03). Whether they are the same processing collection is not settled (T-007).',
      'OPEN: the cause of the eight Bolivian cells still flagged by the night-source mask.',
      'OPEN: when the Aqua and Terra missions will end.',
    ],
    labels: ['LIMITATION', 'OPEN'],
    source:
      'docs/SCIENTIFIC_METHODOLOGY.md, sections 4.7, 4.8 and 8; docs/RISKS_AND_LIMITATIONS.md, S4, S5, S12 to S15; docs/VALIDATION_PLAN.md, section 6; docs/DATA_SOURCES.md, section 4',
  },
]

export interface GridRow {
  fine: string
  analysis: string
  spearman: string
  bothPositive: string
  aquaAtLeast5: string
  chosen: boolean
}

/** The four D-009 rows, as in docs/DECISION_LOG.md. Aqua vs S-NPP, 2012 to 2016. */
export const GRID_EVIDENCE: readonly GridRow[] = [
  { fine: '0.05°', analysis: '0.25°', spearman: '0.672', bothPositive: '13.3%', aquaAtLeast5: '4.5%', chosen: false },
  { fine: '0.05°', analysis: '0.5°', spearman: '0.739', bothPositive: '21.0%', aquaAtLeast5: '8.8%', chosen: true },
  { fine: '0.1°', analysis: '0.25°', spearman: '0.664', bothPositive: '13.2%', aquaAtLeast5: '4.1%', chosen: false },
  { fine: '0.1°', analysis: '0.5°', spearman: '0.733', bothPositive: '21.0%', aquaAtLeast5: '8.4%', chosen: false },
]

export const GRID_EVIDENCE_CONSEQUENCES: readonly string[] = [
  'Aqua night activity is thin (Spearman 0.41 to 0.51), so night strata will rely on pooling.',
  'Only about 9% of cell-months reach Aqua at least 5 cell-days, so cell-level verdicts will often be CANNOT_DETERMINE. Country and continent are the main verdict levels.',
  'The 0.05 degree fine cell is close to a MODIS edge pixel at high latitudes. The 0.1 degree alternative scored slightly lower (0.733).',
]

export const GRID_EVIDENCE_SOURCE =
  'docs/DECISION_LOG.md, D-009 (Aqua vs S-NPP, 2012 to 2016, standard-product data with approved filters and static mask, day and night combined; Member 2 test, PR #27). Chosen by the rule fixed beforehand and approved by the Lead on 2026-11-14 (G1). Columns: "Both > 0" is the share of cell-months where both satellites are active; "Aqua >= 5" is the share of cell-months with at least 5 Aqua cell-days.'

export interface PlannedTest {
  id: string
  title: string
  measures: string
  passRule: string
  appliesTo: string
}

/** Every test of docs/VALIDATION_PLAN.md section 3. Plans only: no status, no result. */
export const PLANNED_TESTS: readonly PlannedTest[] = [
  {
    id: 'A1',
    title: 'Real anomaly preserved (two independent paths)',
    measures: 'pct_of_normal computed from Aqua alone vs from converted S-NPP alone',
    passRule:
      'Same direction (both above or both below normal); peak month within ±1; 90% intervals overlap. Family pass: ≥5 of 6 clean-overlap cases (C1–C6)',
    appliesTo: 'C1–C6',
  },
  {
    id: 'A2',
    title: 'Same fire, two eras',
    measures:
      "Plant the event's real Aqua detections into a quiet pre-2012 month and its real VIIRS detections into a quiet post-2022 month; harmonize both",
    passRule:
      'Harmonized peaks overlap within 90% intervals and the raw record shows a mismatch (otherwise the test is INCONCLUSIVE)',
    appliesTo: 'C1, C4, C6',
  },
  {
    id: 'B1',
    title: 'Satellite-change step removed',
    measures: 'Step ratio at 2012-01 and 2018-04: (series ÷ Aqua-only), 12 months after vs before',
    passRule:
      'Raw: step clearly present. Harmonized: within ±10% of 1 in ≥80% of regions with sufficient data',
    appliesTo: 'All fire regions',
  },
  {
    id: 'B2',
    title: 'Planted sensor jump detected',
    measures: 'Multiply one witness by a random factor from a random date onward (≥50 trials)',
    passRule:
      'Flagged (WITNESS_DISAGREEMENT or a widened interval) within 3 months in ≥90% of trials; false flags in <5% of unplanted series',
    appliesTo: 'Random cells and regions',
  },
  {
    id: 'B3',
    title: 'Known real artifacts surfaced',
    measures: 'Aqua/VIIRS ratio over time; S-NPP end 2026-11-02; outage dates',
    passRule:
      'Drift visible as a ratio trend (reported with its onset estimate); outage months 100% CANNOT_DETERMINE',
    appliesTo: 'Global',
  },
  {
    id: 'C1',
    title: 'Cross-satellite agreement',
    measures: 'Converted S-NPP vs converted NOAA-20, region-months 2018–2021',
    passRule: '≥85% agree within combined 90% intervals',
    appliesTo: 'All fire regions',
  },
  {
    id: 'D1',
    title: 'Uncertainty honest (coverage)',
    measures: 'Holdout 2017–2021: share of actual Aqua values inside the predicted 90% intervals',
    passRule: 'Between 80% and 97%',
    appliesTo: 'All fire regions',
  },
  {
    id: 'D2',
    title: 'Gaps and insufficiency',
    measures: 'Outage months; cells below the data thresholds',
    passRule:
      '100% shown as CANNOT_DETERMINE / NO_DETECTED_ACTIVITY; report % of land cells with a determinable verdict',
    appliesTo: 'Global',
  },
  {
    id: 'E1',
    title: 'Generalization (leave one region out)',
    measures: "Fit without fire region R; predict R's 2017–2021 Aqua series",
    passRule: 'Our method beats the naive raw merge in ≥11 of 14 regions; all regions reported',
    appliesTo: 'All fire regions',
  },
  {
    id: 'CTRL',
    title: 'Control',
    measures: 'Verdicts at satellite-change dates in C8',
    passRule: 'No ABOVE/BELOW verdict at change dates that is absent from the Aqua-only series',
    appliesTo: 'C8',
  },
  {
    id: 'S1',
    title: 'Sensitivity',
    measures:
      'Re-run A1 and B1 without the confidence filter, and with the Aqua-measured baseline (2003–2021)',
    passRule: 'Conclusions unchanged (report any that change)',
    appliesTo: 'C1–C6',
  },
]

export const PLANNED_TESTS_NOTE =
  'These are plans, not results. The validation plan fixes the pass rules before any result exists (pre-registration): they were locked by the Project Lead at Gate G1 (D-028, 2026-11-14), and any later change must be logged with a reason, with the original threshold kept visible. Results, including failures, are published where they exist. Passing these tests would show the method behaves correctly where tested. It would not establish global accuracy. Test IDs C1 (cross-satellite agreement) and case IDs C1 to C8 (validation cases) are different things that share a label in the plan.'

/** Validation cases of docs/VALIDATION_PLAN.md section 2 (proposed; their anomaly magnitudes are unknown until computed). */
export const VALIDATION_CASES: readonly { id: string; case: string; role: string }[] = [
  { id: 'C1', case: 'Indonesia, Sep–Oct 2015 (tropical peat, Equatorial Asia)', role: 'Survival; two eras' },
  { id: 'C2', case: 'Brazilian Amazon, Aug 2019 (tropical deforestation, S. Hemisphere S. America)', role: 'Survival' },
  { id: 'C3', case: 'Pantanal, 2020 (wetland, S. Hemisphere S. America)', role: 'Survival' },
  { id: 'C4', case: 'SE Australia, Dec 2019–Jan 2020 (temperate forest, Australia)', role: 'Survival; two eras' },
  { id: 'C5', case: 'California, Aug–Sep 2020 (Mediterranean, Temperate N. America)', role: 'Survival' },
  {
    id: 'C6',
    case: 'Siberia (Sakha/Yakutia), 2021 (boreal, Boreal Asia)',
    role: 'Survival; two eras (overlap; drift onset to check)',
  },
  {
    id: 'C7',
    case: 'Canada, 2023 (boreal, Boreal N. America)',
    role: 'Stress test: are the intervals honest? (Aqua drift era)',
  },
  {
    id: 'C8',
    case: 'Southern African savanna, no event (savanna, S. Hemisphere Africa)',
    role: 'Control: no spurious anomalies at satellite-change dates',
  },
]

export const REFERENCES: readonly { text: string; url: string }[] = [
  {
    text: 'Schroeder, W. et al. (2014) Remote Sensing of Environment: the VIIRS 375 m active fire product.',
    url: 'https://directreadout.sci.gsfc.nasa.gov/publications_documents/Schroeder_et_al_2014b_RSE.pdf',
  },
  {
    text: 'Giglio, L., Schroeder, W., Justice, C. (2016) RSE: the MODIS Collection 6 active fire algorithm.',
    url: 'https://www.earthdata.nasa.gov/s3fs-public/imported/Giglio2016_C6_Fire.pdf',
  },
  {
    text: 'Giglio, L. et al. (2006) JGR: global distribution of fire from MODIS (CMG gridding normalized by observations).',
    url: 'https://dataserver-coids.inpe.br/queimadas/queimadas/Publicacoes-Impacto/material3os/2006_Giglio_etal_GlobalDistribuiton_JGR_DE3os.pdf',
  },
  {
    text: 'Li, F. et al. (2018) JGR Atmospheres: Aqua MODIS vs S-NPP VIIRS FRP comparison.',
    url: 'https://repository.library.noaa.gov/view/noaa/49896/noaa_49896_DS1.pdf',
  },
  {
    text: 'MDPI Remote Sensing 18(10):1650 (2026): FRP correction and fusion using MYD14 and VNP14IMG (matched within 5 minutes).',
    url: 'https://doi.org/10.3390/rs18101650',
  },
  {
    text: 'VIIRS 750 m active fire ATBD (MODIS C6 heritage).',
    url: 'https://viirsland.gsfc.nasa.gov/PDF/VIIRS_activefire_750m_ATBD.pdf',
  },
  {
    text: 'LAADS: MODIS to VIIRS transition (orbit drift).',
    url: 'https://ladsweb.modaps.eosdis.nasa.gov/learn/modis-to-viirs-transition',
  },
  {
    // No URL is given in docs/SCIENTIFIC_METHODOLOGY.md section 9. Left empty on purpose.
    text: 'Venema, V. et al. (2012) Climate of the Past 8:89–115: benchmarking homogenization algorithms (the synthetic-break validation concept).',
    url: '',
  },
  {
    text: 'Stradiotti et al. (2025): ESA CCI soil moisture merging with inverse-uncertainty weighting.',
    url: 'https://repositum.tuwien.at/bitstream/20.500.12708/218167/1/Stradiotti-2025-Science%20of%20Remote%20Sensing-vor.pdf',
  },
  {
    text: 'Punjab burning-time shift (ISRO/SAC via Tribune).',
    url: 'https://www.tribuneindia.com/news/haryana/farmers-shift-stubble-burning-time-to-dodge-satellite-tracking-isro-study',
  },
]

/** Copied exactly from SP_DOIS and NRT_DOIS in api/fire_api/export.py: 4 standard, 3 near-real-time. */
export const DATASET_DOIS: {
  standard: readonly { name: string; doi: string }[]
  nearRealTime: readonly { name: string; doi: string }[]
} = {
  standard: [
    { name: 'MODIS/Aqua MYD14 V061', doi: '10.5067/MODIS/MYD14.061' },
    { name: 'MODIS/Terra MOD14 V061', doi: '10.5067/MODIS/MOD14.061' },
    { name: 'VIIRS/NPP VNP14IMG V002', doi: '10.5067/VIIRS/VNP14IMG.002' },
    { name: 'VIIRS/JPSS1 VJ114IMG V002', doi: '10.5067/VIIRS/VJ114IMG.002' },
  ],
  nearRealTime: [
    { name: 'MODIS MCD14DL NRT', doi: '10.5067/FIRMS/MODIS/MCD14DL.NRT.0061' },
    { name: 'VIIRS S-NPP VNP14IMGT NRT', doi: '10.5067/FIRMS/VIIRS/VNP14IMGT_NRT.002' },
    { name: 'VIIRS NOAA-20 VJ114IMGT NRT', doi: '10.5067/FIRMS/VIIRS/VJ114IMGT_NRT.002' },
  ],
}
