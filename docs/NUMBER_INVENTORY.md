# Number inventory: every number the app displays (T-039 phase 2)

> **Updated 2026-11-16 for the T-093 UI pass: the answer panel rows (interval bar, reason chips, source line), the timeline and the map's low-zoom drawing rule; the number check still reports 0 mismatches (`docs/validation/T-093-ui-excellence.md`).** Earlier: **updated 2026-11-15 for the finished UI (T-078): the sections "Summary card and sparkline" to "Map source line, imagery and boundaries" and the methods rows were added or rewritten; the results of the check are in `docs/validation/T-078-final-number-check.md`.** For Member 2 and the Lead, to tick off in T-026. Written 2026-11-15 from the code on branch `frontend/T-039-real-verdicts` (app `app/src`, API `api/fire_api`), products T-014 (method 0.1.0, contract 0.1.1). Each row was derived by reading the component and its format helper; the file in the last column is where to look.

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

The satellite chart's hover numbers are formatted with the same one-decimal helper as every other panel (`valueFormatter`, after the T-026 finding of unrounded values), and its axis ticks show whole numbers with thousands separators; the calendar heatmap tooltips use `cellLines`. Plotted positions are the stored values. The CSV is written by the API and rounds nothing.

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
| Satellite chart | Harmonized line and 90% band | `estimate`, `ci90_low`, `ci90_high` | Stored values plotted; hover numbers one decimal (`oneDecimal`, as in the other panels); axis ticks whole numbers with thousands separators | cell-days |
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
| Validation results (T-089) | Number of tests per status (PASS, FAIL, INCONCLUSIVE, NOT_RUN), the filter chip counts | `validation_results.json` `tests[].status` | Computed tally (see above): 18 PASS, 18 FAIL, 2 INCONCLUSIVE for the T-027 file. With `tests: []` the page says no test has been run and shows no counts. | count |
| Validation results (T-089) | One line per test family: status, entry counts, the Lead's reading note for D1 | `validation_results.json` (the family-level entry, else the documented rule in `methods/validationModel.ts`; D1: the pooled entry `D1-REGIONS` is the official one, Lead decision on PR #56) | Status as stored or by the rule; "N entries: a FAIL, b PASS" counted by the app | count |
| Validation results | Each test: id, family, title, case, criterion, threshold, status, measured values, notes | `validation_results.json` `tests[]` | Stored text; each measured value printed as stored under a label made from its key (no rounding), null as "not measured"; FAIL and INCONCLUSIVE details open with the stored notes first | as stored |
| Method sections, planned tests, grid-choice table, case table, limitations | Figures written in the text (for example baseline 2003 to 2022, 15 baseline years, probability threshold 0.8, phi 2.25 and 2.47, kappa 0.0084 and 0.0164, 0.5 and 0.05 degree grid, holdout errors and coverage 0.818 and 0.811, share of judgeable months 29.6%, 52.7%, 34.1%) | `app/src/content/methods.ts`, sources named in each paragraph (`docs/SCIENTIFIC_METHODOLOGY.md`, `docs/DECISION_LOG.md`, `docs/DATA_SOURCES.md`, `docs/VALIDATION_PLAN.md`) | **Hand-written text, not read from a product.** Each carries its label (VERIFIED, APPROVED, LIMITATION, OPEN, HYPOTHESIS). T-026 should check them against the cited document, not against a product. | as stated |

### Summary card and sparkline (T-070, T-072)

| View | Field shown | Source | Format and rounding | Unit |
|---|---|---|---|---|
| Summary card | Title: area name and month | `entity_month.entity_name` (the world reads "World" in the card and "Global" in the stored name and in the story texts), month of the selection | `<name>, <Month> <year>` | none |
| Summary card | Verdict badge | `entity_month.verdict` | Label and icon of `content/verdicts.ts` | none |
| Summary card | Probability sentence | `p_above`, `p_below` or `p_within` of the verdict | `formatProbability` wording, first letter capital, a full stop (for example "More than 99% likely above normal."); none for CANNOT_DETERMINE and NO_DETECTED_ACTIVITY | % |
| Summary card | Big number | `entity_month.pct_of_normal` | `formatPctOfNormal` (`Math.round`), split into the number (Mono 40 px) and the unit "% of normal"; null reads "% of normal: no data" | % |
| Summary card, interval bar (T-093) | Estimate (a dot in the bar and a printed value) | `entity_month.estimate` | `oneDecimal`; null reads "no data" and nothing is drawn; the unit "fire-active cell-days, Aqua-equivalent" is printed once under the bar | cell-days |
| Summary card, interval bar (T-093) | 90% interval (a bar and a printed value) | `ci90_low`, `ci90_high` | `oneDecimal` each, "<low> to <high>"; "interval not available" when the estimate is there, "no data" when it is not | cell-days |
| Summary card, interval bar (T-093) | Normal range (a hatched band and a printed value) | `baseline_p25`, `baseline_p75` | `oneDecimal` each, "<p25> to <p75>"; null reads "not available" | cell-days |
| Summary card, interval bar (T-093) | Median (a dashed tick and a printed value) | `baseline_median` | `oneDecimal`; null reads "not available" | cell-days |
| Summary card, interval bar (T-093) | Bar geometry | The four values above | **Drawing only**: positions on a 0 (or the lowest value) to highest-value scale with a small pad (`summary/intervalBar.ts`); no position or derived value is printed. The SVG description repeats the printed values. | none |
| Summary card, source line | Satellites, data level, method | `witnesses_used`, `data_level`, `method_version` | Names of `content/witnesses.ts`; "standard (SP)" or "near-real-time (NRT)"; "method <version>". Shown once (T-093 removed the duplicate list above it). A "Provisional" marker beside the heading when `data_level` is not SP | none |
| Summary card, "Why" chips (T-093) | Reason chips | `reason_codes` | One chip per code with the short label of `content/reasonCodes.ts`; it opens the text of `content/reasonTexts.ts` with "Learn more" |
| Summary card (before T-093) | Reason lines | `reason_codes` | Texts of `content/reasonTexts.ts`; "No caveat flags are recorded for this month." when empty; the evidence note for a disagreement scale above 1 (two decimals) | none |
| Sparkline (figure, text equivalent and hidden table) | 12 months of the estimate and the normal range | `entity_month.estimate`, `baseline_p25`, `baseline_p75` of the 12 months ending 3 months after the selected one (or at the latest month, never before the first) | One decimal; "no data" for a missing estimate (a gap in the line, never 0); "not available" for a missing range; the number of gaps and months in the text | cell-days |

### Month picker and scrubber (T-087)

| View | Field shown | Source | Format and rounding | Unit |
|---|---|---|---|---|
| Month scrubber | Position, ticks, label | `metadata.first_month` to `latest_month` (293 months for the T-014 products) | Index of the month in the record; year ticks every fifth year | month |
| Timeline (T-093, replaces the scrubber row) | Strip, year labels, current month flag, provisional shading, satellite joins | `metadata.first_month`, `latest_month`, `provisional_months`; join dates from `content/witnessTimeline.ts` (S-NPP 2012-01, NOAA-20 2018-04: reference facts, not product data) | Year labels every 2, 4 or 8 years by width (2002 and 2026 always); "Month YYYY" via `monthLabel` | month |
| Timeline (T-093) | Faint line behind the strip | The selected area's `estimate` (Harmonized) or `raw_combined_cell_days` (Raw), from the series already loaded | **Drawing only**: scaled 0 to the series' highest value; a null or missing month is a gap, never 0; no number is printed | none |
| Month picker | Year select, 12 month buttons per year | `metadata.first_month`, `latest_month`, `provisional_months` | Months outside the record are disabled (here January to June 2002 and December 2026); provisional months carry "provisional" in the name and a dot | month |
| Month picker | Typed month | The user | `YYYY-MM`, validated against the first and latest month | month |

### Story chips and captions (T-072, T-079)

| View | Field shown | Source | Format and rounding | Unit |
|---|---|---|---|---|
| Story chips | Label of each story | `app/src/content/featured.ts` | `<name>, <Mon> <year>` | none |
| Story caption (shown only when the area and the month equal a story) | Headline, caption, notes, context, "[VERIFIED]" label, source line, query, report link | `app/src/content/featured.ts`, generated by `pipeline/featured_stories.py` from the products (`--check` fails if stale) | Text as generated: % of normal whole number, estimates and intervals whole cell-days with thousands separators, probabilities as the app words them | as in the caption |

### Analytics tab (T-083, T-090)

| View | Field shown | Source | Format and rounding | Unit |
|---|---|---|---|---|
| Raw against harmonized, by year (chart, table) | Months used, raw sum, harmonized sum per year | `entity_month.raw_combined_cell_days` and `estimate` of the months that have an estimate | **Computed by the app:** sums over the months with an estimate; whole numbers with thousands separators; a year with fewer than 12 months says "(partial)"; the text says "Sum of monthly estimates; intervals not combined" | cell-days |
| Season profile (chart, table) | 25th, median and 75th percentile of each calendar month, and the selected year's estimate | `entity_month.baseline_p25`, `baseline_median`, `baseline_p75`, `estimate` | Whole numbers with thousands separators; "no data" when missing | cell-days |
| Rank | "<Month> <year> is the Nth highest <Month> of the record (M years with an estimate)", ties, years without an estimate, provisional note | `entity_month.estimate` of the same calendar month in every year | **Computed by the app:** 1 plus the number of years with a strictly larger estimate; M = years with an estimate; ordinal suffix | rank |
| Coverage | "N% of M cells have a determinable verdict" and the verdict counts | `GET /api/map/cells` and the month's cells (`verdict`) | **Computed by the app:** determinable means any verdict except CANNOT_DETERMINE; `Math.round(share x 100)`; the world only until PR #94 (countries and continents: "shown for the world only") | % and cells |
| Compare | % of normal of two areas by month | `entity_month.pct_of_normal` | `Math.round` in the tooltip; a gap for a missing month, never 0 | % |

### Map drawing at world zoom (T-093)

| View | Field shown | Source | Format and rounding | Unit |
|---|---|---|---|---|
| Map fill, verdict layer, zoom 3 and below | Opacity of the WITHIN_NORMAL, CANNOT_DETERMINE and NO_DETECTED_ACTIVITY cells | `verdict` | **Display only** (`components/map/signal.ts`): 12% of the colour's alpha at zoom 3 and below, rising linearly to full at zoom 4; ABOVE and BELOW always full; "Show all verdicts" (`allv=1`) draws all five at full strength. The verdict, tooltip, cell card and panel are unchanged | none |
| Map legend | "Show all verdicts" switch and the low-zoom line | Fixed text (`content/earth.ts`) | No numbers | none |

### Map source line, imagery and boundaries (T-070, T-084, T-085)

| View | Field shown | Source | Format and rounding | Unit |
|---|---|---|---|---|
| Map source line | Product names, "0.5° grid", "method <version>" | Names as in `SP_DOIS` and `NRT_DOIS` (`api/fire_api/export.py`); `metadata.method_version`; the grid text is a constant equal to `metadata.grid.analysis_deg` (D-009) | Text; no date is written by hand | none |
| Imagery panel | Day of the month for the satellite picture | The selected month; default the 15th, days from the 4th in July 2002 (first Aqua imagery day, `docs/DATA_SOURCES.md` section 9) to the end of the month or today | Day number | day |
| Country outlines, India's boundary | Shapes | `app/public/geo/ne_admin_0_countries_india_pov.geojson` (Natural Earth India point of view, `docs/DATA_SOURCES.md`) | Drawing only; no number is shown | none |

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
5. (Fixed in the T-039 review.) The satellite chart's hover numbers were ECharts' default formatting; they now use the app's one-decimal helper. The legend names mark every satellite line as raw ("Raw: Aqua MODIS", "Raw: all satellites combined").
6. **Partial-month indicator: dropped.** `days_available` is in `cell_month_witness` only, so no served product carries it. Following the Lead's decision on PR #62 (option a), the app relies on the `OUTAGE` reason code (the chart marks it, the evidence panel explains it) and shows no partial-month count. No contract change.
