# Number inventory: every number the app displays (T-039 phase 2)

> For Member 2 and the Lead, to tick off in T-026. Written 2026-11-15 from the code on branch `frontend/T-039-real-verdicts` (app `app/src`, API `api/fire_api`), products T-014 (method 0.1.0, contract 0.1.1). Each row was derived by reading the component and its format helper; the file in the last column is where to look.

## Rule: the app formats, it does not compute

The app shows stored values from the API (which serves the products as stored). It never derives an estimate, interval, baseline, % of normal, probability or verdict. What it does do, and nothing else:

| Operation | Where | Effect on what is shown |
|---|---|---|
| Rounds `pct_of_normal` to a whole number (`Math.round`) | `components/map/format.ts` `formatPctOfNormal`; `components/anomalies/rankings.ts` `pctText`; calendar table | Display only. `Math.round` rounds .5 up. |
| Shows `estimate`, `ci90_low`, `ci90_high`, `baseline_median` with one decimal (`toFixed(1)`) | `format.ts` `formatEstimate`; `witness/WitnessTable.tsx`; `calendar/CalendarTable.tsx` | Display only. |
| Shows a probability as a whole percentage, with the T-039 wording: `>= 0.995` reads "more than 99%", `<= 0.005` reads "less than 1%", never "100%" or "0%" | `format.ts` `formatProbability` (used by cell info, calendar tooltip, evidence panel, anomaly list) | Display only; the stored value is unchanged. |
| Shows `disagreement_scale` with two decimals, only when it is above 1 | `evidence/EvidenceBody.tsx` | Display only. |
| Rounds the top of the activity colour scale to a whole number for its label | `map/Legend.tsx`, `calendar/CalendarLegend.tsx` | Label only. |
| Clamps the colour of % of normal at 0% and 200% | `calendar/scales.ts` (`PCT_LOW`, `PCT_HIGH`) | **Colour only.** The number in the tooltip, table and evidence panel is the true value (for example 1777%). |
| Colour scale maximum shared by Raw and Harmonized: map = the largest `raw_combined_cell_days` or `estimate` among the cells of the month on screen (`sharedMax`); calendar = the same over the whole series of the area (`maxActivity`) | `map/scale.ts`, `calendar/grid.ts` | **Colour and the legend's top label only.** It is a maximum of stored values, not a stored number. |
| Counts: rank in a list (`index + 1`); "N of M areas are in neither ranking" = number of areas of the type minus the entries in the two rankings; count of tests per status | `anomalies/rankings.ts` (`notRankedCount`), `AnomalyPanel.tsx`, `methods/validationFormat.ts` (`countStatuses`) | **These are computed by the app** (a subtraction and a tally). The "neither ranking" count is not stored anywhere; the API gives no count of the other verdicts. |
| Orders nothing | `rankAnomalies` only splits the API list into above and below and keeps the API order (the tie-break lives in the API, `api/README.md`) | None. |
| Stacks the baseline and 90% interval bands as `high - low` for drawing | `witness/chartOption.ts` `band` | Drawing only; the band series have their tooltip switched off, so the difference is never shown. |
| Custom-area bounds rounded to 2 decimals in the label and id | `state/bbox.ts` `bboxLabel`, `customId` | Display and id only (the request uses the numbers typed). |

Not controlled by the app: the axis tick labels and the hover tooltip numbers of the two ECharts charts (satellite chart, calendar heatmap tooltips use `cellLines` and are controlled; the satellite chart's axis tooltip is ECharts' default number formatting, which the T-026 check should read by hovering). The CSV is written by the API and rounds nothing.

## Month and probability wording

"Showing a probability" is always `"<wording> likely above|below|within normal"`, for ABOVE_NORMAL (`p_above`), BELOW_NORMAL (`p_below`) and WITHIN_NORMAL (`p_within`) only; no probability is shown for CANNOT_DETERMINE or NO_DETECTED_ACTIVITY. Examples: 0.824 gives "82% likely above normal"; 0.9999999 gives "more than 99% likely above normal"; 0.995 gives "more than 99%"; 0.994 gives "99%"; 0.005 or less gives "less than 1%".

## The table

Product columns are those of `data/products` (`cell_month_harmonized`, `entity_month`, `cells`, `metadata.json`, `validation_results.json`). "Stored" means shown exactly as the API returns it. Units: "cell-days" = fire-active cell-days.

### Map

| View | Field shown | Source product and column | Format and rounding | Unit |
|---|---|---|---|---|
| Month selector | Month label, "Provisional" badge | `metadata.json` `first_month`, `latest_month`, `provisional_months` | "Month YYYY"; every month between first and latest | month |
| Map, tooltip and selected-cell info | Cell id | `cell_month_harmonized.cell_id` | Stored | id |
| same | Verdict (icon, label) | `cell_month_harmonized.verdict` | Label from `content/verdicts.ts` | none |
| same | Probability of the verdict | `p_above`, `p_below` or `p_within` according to the verdict | `formatProbability` (see above) | % |
| same | Compared with normal | `pct_of_normal` | Whole number plus "% of normal"; null reads "no data" | % of baseline median |
| same | Harmonized estimate and 90% interval | `estimate`, `ci90_low`, `ci90_high` | One decimal; null reads "no data", never 0; interval null reads "interval not available" | cell-days, Aqua-equivalent |
| same | Raw combined | `raw_combined_cell_days` | Stored integer | cell-days (raw) |
| same | Notes | `reason_codes` | Short text per code (`content/reasonCodes.ts`) | none |
| same | Data level | `data_level` | "Provisional (NRT or MIXED)" when not SP | none |
| Map (raw layer) | Raw combined, data level | `raw_combined_cell_days`, `data_level` | As above, nothing else | cell-days (raw) |
| Map fill, verdict layer | Colour and icon | `verdict` | Fixed colour per verdict; icon shown only when zoomed in far enough | none |
| Map fill, activity layers | Colour | `raw_combined_cell_days` (raw) or `estimate` (harmonized), null = "no data" colour with outline | Linear on 0 to shared max, clamped to the ramp | cell-days |
| Map legend, activity layers | Top of the scale | Computed maximum of the two columns over the cells of the month | `Math.round`; "no data" if 0 | cell-days |
| Map legend, verdict layer | Verdict list | Fixed | No numbers | none |

### Anomaly list

| View | Field shown | Source | Format and rounding | Unit |
|---|---|---|---|---|
| Anomalies, per entry | Rank | Position in the API's `GET /api/anomalies` answer, after the split into above and below | `index + 1` | rank |
| same | Name, verdict | `entity_month.entity_name`, `verdict` | Stored | none |
| same | Probability | `entity_month.p_above` (above list) or `p_below` (below list) | `formatProbability` | % |
| same | % of normal | `entity_month.pct_of_normal` | Whole number plus "% of normal"; null reads "no data" | % |
| same | "N of M countries are in neither ranking" | M = length of `GET /api/entities?type=...`; N = M minus the two lists | Computed subtraction (see above); includes within normal, cannot determine and no detected activity | areas |
| same | Order | API: `max(p_above, p_below)` descending, then `abs(ln(pct_of_normal/100))` descending (null or non-positive last), then `entity_id` | Not changed by the app; at most 20 per list when expanded, 10 otherwise (`PAGE_SIZE`, `EXPANDED_SIZE`) | none |

### Calendar

| View | Field shown | Source | Format and rounding | Unit |
|---|---|---|---|---|
| Calendar heatmap, % of normal | Cell colour | `entity_month.pct_of_normal` | Diverging colour centred on 100%, **clamped at 0% and 200% for colour only** | % |
| Calendar heatmap, activity | Cell colour | `entity_month.estimate` (harmonized) or `raw_combined_cell_days` (raw) | Linear to the shared series maximum | cell-days |
| Calendar heatmap | Verdict icon | `entity_month.verdict` | Icon per verdict (none on raw) | none |
| Calendar tooltip and accessible label (harmonized) | Verdict and probability, Compared with normal, Harmonized estimate with interval, Notes, Provisional | `verdict`, `p_*`, `pct_of_normal`, `estimate`, `ci90_low`, `ci90_high`, `reason_codes`, `data_level` | As in the map tooltip | as above |
| Calendar tooltip (raw) | Raw combined | `raw_combined_cell_days` | Stored integer | cell-days (raw) |
| Calendar table view | Cell text | `pct_of_normal` (whole number, "no data" if null), or `estimate` (one decimal), or `raw_combined_cell_days` (integer) | As stated | %, cell-days |
| Calendar legend | Scale labels "0%", "100% (normal level)", "200% or more" | Fixed | Fixed text | % |
| Calendar legend | Top of the activity scale | Maximum of `raw_combined_cell_days` and `estimate` over the whole series | `Math.round` | cell-days |
| Calendar rows | Year labels, month abbreviations | `metadata.json` months | Stored | year, month |

### Evidence panel (cell, country, continent, world)

| View | Field shown | Source | Format and rounding | Unit |
|---|---|---|---|---|
| Evidence, Verdict | Verdict, probability, description | `verdict`, `p_*` | As above | none, % |
| Evidence, Numbers | Compared with normal | `pct_of_normal` | Whole number plus "% of normal" | % |
| same | Harmonized estimate | `estimate`, `ci90_low`, `ci90_high` | One decimal, with "(fire-active cell-days, Aqua-equivalent)" | cell-days |
| Satellites used | Names | `witnesses_used` | Names from `content/witnesses.ts` | none |
| same | Disagreement scale | `disagreement_scale` | Two decimals, only when above 1 | ratio (S) |
| Raw contribution of each satellite | Per-satellite raw count | `entity_month.raw_by_witness` (JSON object, decoded by the API) | Stored integers; absent satellite is not listed; none at all reads "no data" | cell-days (raw) |
| Why | Reason texts and codes | `reason_codes` | Text from `content/reasonTexts.ts` plus the code | none |
| Footer | Method version, contract version | `method_version` (record), `metadata.json` `contract_version` | Stored | version |
| Heading | "Evidence: area, Month Year" | selection | Text | none |

### Satellite chart and table

| View | Field shown | Source | Format and rounding | Unit |
|---|---|---|---|---|
| Satellite chart | Harmonized line and 90% band | `estimate`, `ci90_low`, `ci90_high` | Stored values plotted; tooltip and axis numbers are ECharts defaults | cell-days |
| same | Baseline band and median | `baseline_p25`, `baseline_p75`, `baseline_median` | Same | cell-days |
| same | Raw combined line | `raw_combined_cell_days` | Same | cell-days (raw) |
| same | One line per satellite | `raw_by_witness` | Same; missing month is a gap, not 0 | cell-days (raw) |
| same | Vertical marks | `reason_codes` OUTAGE and AQUA_DRIFT_ERA, `data_level` | Month positions only | none |
| Satellite table view | Month, estimate, 90% interval, baseline median, raw combined, per-satellite raw, notes | same columns | One decimal for estimate, interval, baseline median and per-satellite values; raw combined as an integer; "no data" for null | cell-days |
| Satellite timeline | Record start and end dates of each satellite | `content/witnessTimeline.ts` (written text, source `docs/DATA_SOURCES.md` section 4) | Written dates | date |

### CSV export (`GET /api/export.csv`)

| View | Field shown | Source | Format and rounding | Unit |
|---|---|---|---|---|
| Header lines (`#`) | data status, area, method and contract version, generated_at, data snapshot dates, meaning, citation, notes, dataset DOIs | `metadata.json` plus fixed text in `api/fire_api/export.py` | Text | none |
| Header row | The 25 `entity_month` columns, then `raw_AQUA_MODIS`, `raw_TERRA_MODIS`, `raw_SNPP_VIIRS`, `raw_NOAA20_VIIRS`, `raw_NOAA21_VIIRS` | `entity_month.parquet` and `raw_by_witness` | Contract order | none |
| Rows | Every number of the series | `entity_month.parquet` | Floats written with Python `repr` (full precision, no rounding), integers as integers; null is an empty cell, never 0; lists joined with `;` | as in the contract |

### Methods and validation page

| View | Field shown | Source | Format and rounding | Unit |
|---|---|---|---|---|
| Validation results header | Generated, method version, contract version, synthetic | `validation_results.json` | Stored text | none |
| Validation results | Number of tests per status (PASS, FAIL, INCONCLUSIVE, NOT_RUN) | `validation_results.json` `tests[].status` | Computed tally (see above). With `tests: []` the page says no test has been run and shows no counts. | count |
| Validation results | Each test: id, family, title, case, criterion, threshold, status, measured values, notes | `validation_results.json` `tests[]` | Stored text; each measured value printed as `String(value)`, null as "not measured" | as stored |
| Method sections, planned tests, grid-choice table, case table, limitations | Figures written in the text (for example baseline 2003 to 2022, 15 baseline years, probability threshold 0.8, phi 2.25 and 2.47, kappa 0.0084 and 0.0164, 0.5 and 0.05 degree grid, holdout errors and coverage 0.818 and 0.811, share of judgeable months 29.6%, 52.7%, 34.1%) | `app/src/content/methods.ts`, sources named in each paragraph (`docs/SCIENTIFIC_METHODOLOGY.md`, `docs/DECISION_LOG.md`, `docs/DATA_SOURCES.md`, `docs/VALIDATION_PLAN.md`) | **Hand-written text, not read from a product.** Each carries its label (VERIFIED, APPROVED, LIMITATION, OPEN, HYPOTHESIS). T-026 should check them against the cited document, not against a product. | as stated |

### Other places

| View | Field shown | Source | Format and rounding | Unit |
|---|---|---|---|---|
| Selection panel | Area name and id | `GET /api/entities` (`entity_name`, `entity_id`) | Stored | none |
| Area picker | Country list, continent list | `GET /api/entities` | Stored names | none |
| Custom area label and id | West, south, east, north | Typed by the user | 2 decimals in the label and in the id (`custom_w..._s..._e..._n...`) | degrees |
| Provisional notices | "Provisional" badge and notice | `metadata.json` `provisional_months`, `data_level` | Text | none |
| Raw-only guard (kept, not triggered by the T-014 products) | "Not available yet" in place of harmonized numbers | `method_version` ending in `-raw-only` | Text | none |
| Offline copy | Same as the live app: the files are the API's own answers | `app/public/data` written by `fire_api.static_export` | Same formatting code | as above |

## Things T-026 should look at specifically

1. The probability wording: a stored `p_above = 0.9999999999999996` reads "more than 99%". The stored value, the CSV and the API are unchanged.
2. The % of normal shown is rounded to a whole number; the CSV holds the full value (`264.8615747270596` for Indonesia 2015-09 is shown as "265% of normal").
3. The calendar and the map colour clamp at 200% of normal and at the shared maximum; the tooltip and the table hold the true value.
4. The "N of M in neither ranking" line and the test-status counts are computed by the app (a subtraction and a tally).
5. The satellite chart's hover numbers are ECharts' default formatting, not the app's `toFixed(1)`.
6. **Partial-month indicator: dropped.** `days_available` is in `cell_month_witness` only, so no served product carries it. Following the Lead's decision on PR #62 (option a), the app relies on the `OUTAGE` reason code (the chart marks it, the evidence panel explains it) and shows no partial-month count. No contract change.
