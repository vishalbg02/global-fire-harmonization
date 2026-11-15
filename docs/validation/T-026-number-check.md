# T-026: every number the app displays, checked against the products

> Member 2 (sign-off: Member 1) · 2026-11-15 · task prompt `docs/task-prompts/T-026-number-check.md` · checker `pipeline/number_check.py` + `pipeline/number_check_app.mjs` (tests `pipeline/tests/test_number_check.py`) · raw output `data/interim/qa/T-026_number_check.json` (not committed)
> **Under test:** the app and API of PR #62 (`frontend/T-039-real-verdicts` @ ce0e155, not yet merged), the real products T-014 (method 0.1.0, contract 0.1.1), and `docs/NUMBER_INVENTORY.md` as the list of what is displayed. Nothing in `app/`, `api/` or `data/products/` was changed.

## 1. Result

**6,492,020 values checked, 0 mismatches, 0 defects.** No number the API serves or the app's formatting code shows differs from the product or from the rule of the inventory. The check covers the fixed views and every row of `entity_month`, plus 582,356 `cell_month_harmonized` rows (every row of the five demo months, every row at a formatting edge, and a fixed random sample of 300,000 of the rest). Two notes (section 4) and the parts this check cannot reach (section 5) are listed so that nothing reads as covered that is not.

## 2. What was checked, and how

| Class | What | How |
|---|---|---|
| A | The API serves exactly the stored value | The real FastAPI app in process on `data/products`; every numeric field is the same double, every null a null (never 0), lists and `raw_by_witness` equal; the anomaly set and order recomputed independently from `entity_month` by the documented rule (larger of `p_above` and `p_below`, then distance from normal, then id) |
| B | The app's formatting shows what the inventory says | The app's own TypeScript functions (`formatProbability`, `formatPctOfNormal`, `formatEstimate`, `verdictProbability`, `pctText`, `probabilityText`) called through node on the stored values and compared with an independent Python port of the inventory rules (JavaScript `Math.round` and `toFixed` emulated exactly; the port is itself tested against node on more than 600 values) |
| C | What the app computes itself | `rankAnomalies` split and order, "N of M areas in neither ranking", test-status counts (for this branch's `validation_results.json` and for the T-027 file of PR #70), the maxima behind the legend top labels (map and calendar), the custom-area label |
| D | The CSV export | The export of Indonesia: header lines, the 25 contract columns plus the five `raw_*` columns, one row per stored month, every cell equal to the stored value (full precision), null an empty cell |
| E | Hand-written figures of the methods page | phi, kappa, baseline 2003 to 2022 and 15 of 20 years, the D1 coverages and unit counts, the judgeable shares (29.6%, 52.7%, 34.1%, 2.9%), 65% no detected activity, 189 of 293 world months, recomputed from the code constants, `validation_results.json` and the products |

Fixed views: Indonesia 2015-09 and 2015-10, Brazil 2019-08, Canada 2023-07, the world for the latest month; the continents; anomaly lists of 2015-09, 2023-08 and the latest month; the map of 2015-09 and 2023-07 (every cell, 56,238 each); the series of IDN, BRA, CAN and GLOBAL; the CSV of IDN.

| Check | Values checked | Match | Mismatch |
|---|---|---|---|
| A anomaly order | 3 | 3 | 0 |
| A anomaly set | 3 | 3 | 0 |
| A anomaly values | 470 | 470 | 0 |
| A evidence raw_by_witness | 5 | 5 | 0 |
| A evidence record | 125 | 125 | 0 |
| A map cell bounds | 449,904 | 449,904 | 0 |
| A map cell count | 6 | 6 | 0 |
| A map cell present | 112,476 | 112,476 | 0 |
| A map cell values | 2,137,044 | 2,137,044 | 0 |
| A metadata | 1 | 1 | 0 |
| A series length | 5 | 5 | 0 |
| A series order | 5 | 5 | 0 |
| A series records | 38,090 | 38,090 | 0 |
| A validation file | 1 | 1 | 0 |
| B % of normal text | 650,918 | 650,918 | 0 |
| B anomaly row text | 23,402 | 23,402 | 0 |
| B estimate and interval text | 650,918 | 650,918 | 0 |
| B probability wording | 1,768,875 | 1,768,875 | 0 |
| B verdict probability text | 650,918 | 650,918 | 0 |
| C custom-area label | 15 | 15 | 0 |
| C legend maximum | 7 | 7 | 0 |
| C not-ranked count | 6 | 6 | 0 |
| C ranking split | 6 | 6 | 0 |
| C test-status counts | 2 | 2 | 0 |
| D csv columns | 1 | 1 | 0 |
| D csv header lines | 6 | 6 | 0 |
| D csv rows | 1 | 1 | 0 |
| D csv values | 8,790 | 8,790 | 0 |
| E methods text | 17 | 17 | 0 |
| **Total** | **6,492,020** | **6,492,020** | **0** |

## 3. What the numbers show (VERIFIED)

- **Stored values are served unchanged.** All 2,137,044 map values, 38,090 series values, 125 evidence values and the validation and metadata files are the stored doubles, nulls included.
- **The formatting rules are implemented as the inventory says**, for 1,768,875 probabilities, 650,918 % of normal values and 650,918 estimates with intervals, including every value within 1e-9 of the 0.995 and 0.005 wording thresholds and every % of normal at a .5 boundary. A probability of 1.0 or 0.9999999999999996 reads "more than 99%"; none reads "100%" or "0%".
- **The anomaly order matches the documented rule** for 2015-09, 2023-08 and the latest month. In 2015-09 the first countries above normal are South Sudan, Indonesia and Papua New Guinea. Indonesia is **rank 2** of 21, not first, because the approved tie-break (distance from normal) puts South Sudan (784% of normal) above it (265%). In 2023-08 Canada is rank 1. This matters for the demo script: say "Indonesia is among the top two", not "the top".
- **The test-status tally is right.** For this branch's `validation_results.json` (no tests) the page shows no counts. For the T-027 file (PR #70) the app's `countStatuses` gives FAIL 18, INCONCLUSIVE 2, PASS 18, NOT_RUN 0, equal to a direct tally.
- **The methods-page figures equal their sources.** The sentence "189 of the 293 world months are CANNOT_DETERMINE with WIDE_INTERVAL" is exact (the products also hold 4 further CANNOT_DETERMINE months with other reasons, 193 in all). A first version of this checker compared with 193 and was corrected to the sentence's own definition before the final run.

## 4. Notes (not defects)

1. **Custom-area label, negative ties.** `bboxLabel` and `customId` round with `Math.round(v * 100) / 100`, so a coordinate that ends in exactly 5 at the third decimal rounds towards +infinity: 95.005 shows as 95.01 (as typed), but -6.125 shows as -6.12, where a user may expect -6.13. Display and id only; the request uses the typed number. For Member 3 as a cosmetic point.
2. **Hand-written text.** Other numbers in `app/src/content/methods.ts` (dates, DOIs, drift onset months, BIC, sizes) carry their own labels and are not read from a product. Only the figures the inventory names were compared.

## 5. What this check cannot reach (a browser pass with the Lead covers it)

The checker calls the app's functions, not its pixels. Not covered:
- the hover and axis numbers drawn by ECharts (satellite chart and calendar heatmap, which use ECharts' default number formatting);
- the `toFixed` formatting written inside React components that node cannot import (`EvidenceBody.tsx` disagreement scale with two decimals, `WitnessTable.tsx` one-decimal values);
- colour values and the 0% and 200% colour clamp;
- the month selector and the provisional badges;
- the offline copy (`app/public/data`): it holds the API's own answers, so class A covers the same endpoints, but its files were not read one by one;
- the T-060 demo script, which does not exist yet (the demo scenes of T-050 stand in).

## 6. Sign-off (for the Lead; not ticked by this task)

Rows of `docs/NUMBER_INVENTORY.md`:

- [ ] Map: cell info, activity legend, month selector
- [ ] Anomaly list: rank, probability, % of normal, "N of M in neither ranking", order
- [ ] Calendar: tooltip, table, legend, colour clamp
- [ ] Evidence panel: verdict, probability, numbers, satellites, disagreement scale, raw contribution, footer
- [ ] Satellite chart and table: ECharts hover numbers, one-decimal table values
- [ ] CSV export
- [ ] Methods and validation page: status counts, hand-written figures
- [ ] Custom area label

## 7. Reproduce

```bash
python -m pytest pipeline/tests/test_number_check.py -q
python pipeline/number_check.py --validation-extra path/to/the/T-027/validation_results.json    # about 2.5 minutes; take the heavy-job lock first
```

Re-run it after PR #62 or the products change. The numbers above come from the run of 2026-11-15 on the products of T-014 and the app at ce0e155.
