# T-023: test A2 (same fire, two eras): results

> Run 2026-11-15 on the T-011/T-013 products on `main` (`cell_month_witness`, `cells`, `calibration`; method `harmonize.METHOD_VERSION` = `0.1.0-combined-no-baseline`). Harness `pipeline/validation_a2.py`; design fixed in `docs/task-prompts/T-023-test-a2.md` before any real run (one amendment, also before the first run: `cell_days` is not capped by `days_in_month`). Thresholds are those of `docs/VALIDATION_PLAN.md` section 3 and were not changed after seeing a result. Labels: [VERIFIED] computed here; [ASSUMPTION] a reading the plan does not fix.

**Official results.** A2-C1 **FAIL**, A2-C4 **FAIL**, A2-C6 **FAIL**; family **A2: FAIL** (family rule is an [ASSUMPTION], section 6). In all three cases the raw record shows the expected large post-2022 inflation (raw S-NPP over raw Aqua 2.4 to 4.0), and the harmonized S-NPP estimate stays below the harmonized Aqua estimate, so the 90% intervals do not overlap.

| Case | Quiet month | Event month | Raw cell-days: Aqua 2010 / S-NPP 2023 (ratio) | Harmonized 2010 Aqua (90%) | Harmonized 2023 S-NPP (90%) | S-NPP / Aqua, difference in sd | Overlap | Status |
|---|---|---|---|---|---|---|---|---|
| C1 Indonesia | December (2010-12, 2023-12) | 2015-09 | 15,751 / 62,818 (3.99, inflation) | 15,751 (13,752 to 17,750) | 10,238 (8,714 to 11,761) | 0.650, -3.6 sd | no | **FAIL** |
| C4 SE Australia | December | 2019-12 | 6,842 / 16,622 (2.43, inflation) | 6,842 (5,970 to 7,714) | 3,532 (3,063 to 4,000) | 0.516, -5.5 sd | no | **FAIL** |
| C6 Sakha/Yakutia | January | 2021-08 | 21,094 / 51,046 (2.42, inflation) | 21,094 (18,457 to 23,731) | 7,343 (5,852 to 8,835) | 0.348, -7.5 sd | no | **FAIL** |
| **Family A2** | | | | | | | | **FAIL** (0 PASS, 3 FAIL, 0 INCONCLUSIVE) |

Units: Aqua-equivalent cell-days for the harmonized columns; raw cell-days (day + night, unconverted) for the raw column. All numbers [VERIFIED].

## 1. What was done
- **Cases, boxes, peak windows** as in `validation_a1.CASES` (VALIDATION_PLAN section 2a): C1 548 cells, C4 296, C6 2,174 (cell centre in the box, edges included).
- **Quiet month** (plan section 2a, literal) [VERIFIED]: harmonized series of the box (`aggregate` + `records_from`, all witnesses), calendar-month median over 2003-2022 (at least 15 of 20 years), lowest median, earliest on a tie. C1: December (median 114.1; the next lowest is January at 242). C4: December (130.3; January 160). C6: January (0.0, tied with February and December, earliest taken). The 5 cell-day floor of D-028 is not applied. The same calendar month is used in 2010 and in 2023.
- **Event month** (rule 9.2 of the task prompt): the peak-window month with the most raw Aqua cell-days: C1 2015-09 (15,751 against 11,346 in October), C4 2019-12 (6,842 against 4,373 in January), C6 2021-08 (21,094 against 20,635 in July).
- **Planting** at the level of `cell_month_witness` rows of the box cells, in memory and in a temporary product directory under `data/interim/T-023/` (the products on disk are never written): the quiet month's rows (all witnesses) are removed; the event month's real Aqua rows go into (2010, quiet month), its real S-NPP rows into (2023, quiet month). Detections, cell-days and FRP sums are the event's; `days_in_month` and `days_available` are the target month's; `data_level` is the quiet month's (`SP` everywhere here). Totals preserved exactly (checked per case: `totals_preserved: true`); the planted months contain one witness each (no other witness left).
- **Harmonization** with the real v0.1 method (`harmonize.aggregate` + `records_from`, `harmonize.py` untouched), each planted month a single-witness estimate (`SINGLE_WITNESS`).
- **Identity check** [VERIFIED]: the planted 2010 Aqua estimate equals the Aqua-only estimate of the real event month exactly in all three cases (15,751; 6,842; 21,094).
- **Criterion** (fixed in advance): PASS needs a raw mismatch (raw S-NPP / raw Aqua at least 1.5 or at most 1/1.5) AND overlapping 90% intervals (estimate +- 1.645 sd, floor 0, touching counts as overlap); FAIL if there is a raw mismatch and the intervals do not overlap; INCONCLUSIVE if the raw record shows no mismatch (the plan's own rule) or a planting/estimate is missing. The raw mismatch is present in all three cases (ratios 3.99, 2.43, 2.42; each also at least 2.0, a "large inflation" in the descriptive sense), so none is INCONCLUSIVE.

## 2. Reading of the result
- [VERIFIED] The raw record is strongly inflated in the VIIRS era (S-NPP reports 2.4 to 4.0 times the Aqua cell-days of the same event), as the plan expects. The conversion removes most of this: harmonized S-NPP is 0.35 to 0.65 of harmonized Aqua instead of 2.4 to 4.0, but it overshoots, so S-NPP lands below Aqua by 3.6 to 7.5 combined standard deviations.
- [VERIFIED] This is the same direction as the A1 finding on the same boxes (T-020: converted S-NPP-only below Aqua-only for C3 to C6; for C4 0.58 and C6 0.80 of the Aqua pct_of_normal). A2 is a different design (a single month planted in another month and year) but not independent of A1: both use the same conversion ratios and the same real detections.
- [ASSUMPTION, important] **Season of the ratio.** A planted month is converted with the ratios of the target month's season (DJF for December and January), because that is how the pipeline treats any real record of that month. The event happened in another season for C1 (SON) and C6 (JJA); the ratios differ by season, and for C6 the effect is large. The exploratory variant (not part of the status; `measured.exploratory_event_season_ratios`) converts the planted S-NPP month with the event's season ratios instead:

| Case | Primary: S-NPP 2023 (90%), S-NPP / Aqua, overlap | Exploratory, event-season ratios: S-NPP 2023 (90%), S-NPP / Aqua, overlap |
|---|---|---|
| C1 | 10,238 (8,714 to 11,761), 0.650, no | 13,638 (11,842 to 15,435), 0.866, **yes** |
| C4 | 3,532 (3,063 to 4,000), 0.516, no | 3,532 (3,063 to 4,000), 0.516, no (event and target are both DJF) |
| C6 | 7,343 (5,852 to 8,835), 0.348, no | 15,899 (13,559 to 18,239), 0.754, no |

  [VERIFIED] With event-season ratios the planted S-NPP value equals the real event month's S-NPP-only estimate (13,638 for C1, 15,899 for C6), as it must. Under that alternative reading C1 would overlap (its raw mismatch is present, so it would PASS), C4 and C6 would still FAIL, and the family would still FAIL. The family result does not depend on this choice; the C1 and C6 case results do. It is shown only so that the Lead can see the sensitivity; it is not used and nothing was tuned on it.
- [HYPOTHESIS, not tested here] The seasonal dependence of the S-NPP / Aqua ratios and the fact that they were fitted on 2012-2016 are candidates for the shortfall; T-011's calibration and test B3 are the places to look. This task does not change the method.

## 3. Quiet-month context
Median (2003-2022) of the box's harmonized series per calendar month [VERIFIED, in `measured.baseline_medians_by_calendar_month`]: C1 Jan 242, Feb 480, Mar 595, Apr 349, May 545, Jun 1,040, Jul 1,434, Aug 4,629, Sep 6,076, Oct 1,424, Nov 278, Dec 114. C4: Jan 160, Feb 212, Mar 569, Apr 1,460, May 1,027, Jun 218, Jul 335, Aug 570, Sep 481, Oct 288, Nov 167, Dec 130. C6: Jan 0, Feb 0, Mar 1, Apr 16, May 187, Jun 599, Jul 3,597, Aug 1,518, Sep 195, Oct 27, Nov 1, Dec 0. C1 and C4 choose December, in the C4 case the same calendar month as the event (2019-12), in different years. A `pct_of_normal` context is given for C1 and C4 (the planted values are thousands of percent of the quiet month's baseline, as expected for a real extreme event planted into a quiet month) and not for C6, where the quiet baseline median is 0 (below the 5 cell-day floor).

## 4. Caveats
- [VERIFIED] The target months are not shorter than the event for C4 and C6 (31 days both); for C1 the event month (September, 30 days) goes into a 31-day December. No density correction was applied (cell-days are fine-grid cell-days and are planted as they are).
- A planted month holds one witness. The real 2023 month would also have Aqua and NOAA-20, and NOAA-20 did not exist for C1 (2015). The test checks the conversion of S-NPP to the Aqua scale, not the combination of witnesses.
- The S-NPP ratios were fitted on 2012-2016, so the C1 event (2015) lies inside the fit period; C4 (2019-20) and C6 (2021) lie outside it.
- Planting is partly circular (it reuses real detections and the method's own ratios, VALIDATION_PLAN section 5); this does not make the FAIL less real: the same event harmonizes to a lower value through the S-NPP path than through the Aqua path.
- Nothing was tuned: the quiet month, event month, 1.5 threshold and overlap rule were fixed before the run; the pre-registered primary reading is the one reported as official.

## 5. Assumptions the Lead should confirm
1. Quiet month from the combined harmonized series (not Aqua-only), 15-year minimum, no 5 cell-day floor, earliest calendar month on a tie.
2. One event month per case: the peak-window month with most raw Aqua cell-days.
3. A planted month holds one witness only (Aqua 2010, S-NPP 2023); NOAA-20 not used.
4. Season of the ratio = the target month's season (primary); the event-season variant is exploratory.
5. Raw mismatch = raw ratio at least 1.5 or at most 1/1.5 (either direction).
6. Family rule: all three cases must PASS; an INCONCLUSIVE case would not count as a PASS and, as in the A1 family entry, make the family FAIL once no case is left to run (no case is INCONCLUSIVE here, so the family is FAIL either way).

## 6. Reproduce
```
python pipeline/validation_a2.py            # all three cases; writes data/interim/qa/T-023_validation_entries.json
python pipeline/validation_a2.py --case C4  # one case (no family entry)
python pipeline/validation_a2.py --refresh  # recompute the cached series and rows (reads cell_month_witness: take the heavy-job lock first)
python -m pytest pipeline/tests/test_validation_a2.py -q -p no:cacheprovider
```
The cache (`data/interim/T-023/`: the three box series and the extracted rows) lets a rerun skip the heavy reads. Entries file: test ids `A2-C1`, `A2-C4`, `A2-C6`, `A2`.
