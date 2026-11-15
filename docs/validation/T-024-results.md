# T-024 results: tests B2 (planted sensor jump), C1 (cross-satellite agreement) and CTRL (control box C8)

> Run on the final T-011 products (contract 0.1.1, method `0.1.0-combined-no-baseline`, the v0.1 conversion), 2026-11-15, with `python pipeline/validation_b2_c1_ctrl.py all` (code and tests: `pipeline/validation_b2_c1_ctrl.py`, `pipeline/tests/test_validation_b2_c1_ctrl.py`; task prompt: `docs/task-prompts/T-024-test-b2-c1-ctrl.md`). Thresholds are the ones locked at G1 (D-028). Every choice the plan leaves open is written in section 15 of the task prompt, which is the first commit of the branch, before any real run. Nothing was changed after seeing the numbers; the one addition after the first run is a diagnostic table for CTRL (`explain_months`, section 4.3) that carries no status. Labels: [VERIFIED] measured here, [ASSUMPTION], [HYPOTHESIS], [OPEN].

## 1. Verdicts

| Test | Status | In one line |
|---|---|---|
| **B2** planted sensor jump detected | **FAIL** | Detection 84.5% (169 of 200; needs 90%) and false flags 25.0% (50 of 200 unplanted twins; needs under 5%). Fire regions: 100% detected but 39% of unplanted twins flagged; single cells: 69% detected, 11% flagged. |
| **C1** cross-satellite agreement (S-NPP against NOAA-20) | **PASS**, with an in-sample caveat | 97.6% of 630 fire-region-months agree within the combined 90% intervals (needs 85%). The window is in sample for NOAA-20's calibration; the months out of sample for both (2022-01 to 2024-04, supplementary) give 98.4%. |
| **CTRL** control, box C8, change dates 2012-01 and 2018-04 | **FAIL** | 3 spurious verdicts in the 50 evaluated months (needs none): two of them in 2011, where the harmonized estimate equals the Aqua-only estimate exactly and only the baseline differs; one (2012-09) at a probability that crosses the 0.8 line. |
| *Supplementary* B2-CODE-ONLY (flag = reason code only) | FAIL | Detection 73.5%, false flags 13.0%. |
| *Supplementary* B2-FALSE-FLAG-MONTHLY | FAIL (union rule), see 3.4 | 5.6% of unplanted entity-months flagged by the union rule (1.8% by the reason code alone); 27.1% of entities are flagged in at least one month. |
| *Supplementary* C1-OVERLAP (overlapping intervals) | PASS | 99.8%. |
| *Supplementary* C1-OUT-OF-SAMPLE-2022-2024 | PASS | 98.4% of 322 region-months, out of sample for both fits. |
| *Supplementary* CTRL-SHARED-BASELINE (one Aqua-measured baseline for both series) | FAIL | 2 spurious verdicts (2012-09 and 2017-10). |

Entries in the contract section 6 shape: `data/interim/qa/T-024_validation_entries.json` (not committed; the Lead integrates them in T-027). Full numbers: `data/interim/qa/T-024_{b2,c1,ctrl}_report.json` (B2 includes the 200 trials with entity, witness, jump month, factor and flags).

## 2. What was done

### 2.1 B2
1. A pool of 2,000 single cells was drawn (seed 20261115) from the cells of a real fire region, next to the 14 fire regions. All were aggregated for 2012-01 to 2021-12 with `harmonize.aggregate` (cached under `data/interim/T-024/`).
2. Eligible jump candidates (entity, jump month d, witness w): in each of the months d, d+1, d+2 the unplanted record has an estimate of at least 5 Aqua-equivalent cell-days (the D-028 step 4 size), uses w and uses at least one other witness. Result: 14 of 14 regions (3,763 candidate pairs) and 420 of 2,000 cells (14,543 pairs); the other 1,580 cells never have three consecutive months that active with two witnesses. [VERIFIED]
3. 200 trials (100 regions, 100 cells; plan minimum 50): an entity uniformly among the eligible ones, then a (d, w) pair, then a factor with |ln f| uniform on [ln 1.5, ln 3], up or down with equal probability. 89 distinct cells appear in the 100 cell trials.
4. The jump is planted in memory (`plant_jump`): for the entity and witness from month d on, raw cell-days and the converted estimate times f, the counting variance times f, the ratio variance times f^2. The products on disk are not touched. The records of d, d+1, d+2 are recomputed with `harmonize.records_from`.
5. Flagged = `WITNESS_DISAGREEMENT` (S > 2) or a disagreement scale of at least 1.5 [ASSUMPTION 2]. Detection = flagged in any of the three months. False flag = the same rule on the unplanted twin of the trial (same entity, same three months) [ASSUMPTION 3]. PASS needs detection of at least 90% and false flags under 5%.

### 2.2 C1
For each of the 14 fire regions the S-NPP-only and the NOAA-20-only paths are built from the same aggregated table (`validation_a1.restrict_witness`, `records_from`). A unit is a fire-region-month with an estimate from both (complete months) and both estimates at least 5 Aqua-equivalent cell-days. They agree when |e_S - e_N| is at most 1.645 x sqrt(sd_S^2 + sd_N^2) (the 90% interval of the difference). PASS at 85% or more; INCONCLUSIVE below 100 units.

### 2.3 CTRL
Box C8 (20, -20, 35, -8): 720 analysis cells, 2003-01 to 2022-12. Two series from the same aggregation: harmonized (all witnesses) and Aqua-only. Verdicts by the D-028 rules (`validation_e1_s1.verdict_for`, amendment A with the raw cell-days of the month), the harmonized series against its own harmonized 2003-2022 baseline, the Aqua-only series against the Aqua-measured 2003-2022 baseline. Evaluated months: the 25 months from 12 before to 12 after 2012-01 and 2018-04 (2011-01 to 2013-01 and 2017-04 to 2019-04). Spurious: a harmonized ABOVE or BELOW verdict that the Aqua-only series does not give in the same month. PASS needs none (and at least 12 determinable months, else INCONCLUSIVE).

## 3. B2 results

### 3.1 Headline
| | Detection (flag in the jump month or the two after) | False flags (unplanted twin, same 3 months) |
|---|---:|---:|
| All 200 trials (official) | **84.5%** (169/200; Wilson 95%: 78.8% to 88.9%) | **25.0%** (50/200; 19.5% to 31.4%) |
| 100 fire-region trials | 100% (100/100) | 39% (39/100) |
| 100 single-cell trials | 69% (69/100) | 11% (11/100) |
| Reason code only, all trials (B2-CODE-ONLY) | 73.5% (147/200) | 13.0% (26/200) |
| Detected and twin not flagged | 60.0% (120/200) | |

Both criteria fail. In 120 trials the jump was flagged and the unplanted twin was not; in 49 trials both were flagged (the natural flag may be what was seen). [VERIFIED]

### 3.2 Where the detection fails
| By | Detection |
|---|---|
| Fire region | 100% (96 of the 100 in the jump month itself) |
| Single cell | 69% |
| Witness jumped: Aqua / S-NPP / NOAA-20 | 80.0% (72/90) / 86.4% (70/81) / 93.1% (27/29) |
| Jump size, terciles of the factor (1.50-1.93 / 1.93-2.32 / 2.33-2.99) | 77.6% / 84.8% / 91.0% |
| Direction: down / up | 77.5% / 91.8% |
| By jump year (2012 to 2021) | 71% to 96%, no trend, 10 to 31 trials a year |

All 31 undetected trials are single cells, and downward jumps are missed more often than upward ones. A possible reason is that a witness reading too low has a smaller variance, so the disagreement is smaller in standard deviations [HYPOTHESIS, not tested]. This describes where the method has little power; it is not a tuning input. [VERIFIED for the rates]

### 3.3 False flags
At fire-region level the unplanted data already trip the flag often: 20.5% of region-months by the union rule and 10.5% by the reason code alone (337 and 172 of 1,640 eligible region-months), against 4.6% expected per two-witness month if the witness differences followed the stated variance exactly (chi-square with one degree of freedom, S > 2) [HYPOTHESIS: the model is right]. For cells it is 4.1% (union) and 0.9% (code) of 16,241 eligible cell-months. So in regions the witnesses differ more than the variance model allows, which fits the D1 findings (the intervals are too narrow in places); in cells the counts are small and the intervals wide, so the flag rarely fires, for planted jumps as well. [VERIFIED for the rates; the explanation is a HYPOTHESIS]

### 3.4 Supplementary readings (same thresholds, not the official entry)
- Per entity-month, all eligible unplanted months of 1,000 entities with at least one such month, the 14 regions and 986 cells (17,881 entity-months): union rule 5.6% (999), reason code 1.8% (316). The union rule is just above the 5% line, the code alone is below it. The status of `B2-FALSE-FLAG-MONTHLY` uses the union rule and is FAIL.
- Per series, any month 2012-2021: 27.1% of the 1,000 entities are flagged at least once (union), 10.3% by the code alone.
- Whichever unit is used, the planted-jump detection (84.5%, 73.5% by code) is below 90%.

### 3.5 What is withdrawn or narrowed
We cannot claim that a sensor jump of 1.5 to 3 times in one witness is flagged reliably. It is at the fire-region level (100% of 100 trials, mostly in the first month), not for single cells (69%), and the flag at region level also fires too often without a jump. A user reading "no WITNESS_DISAGREEMENT" should not read it as "the witnesses agree" for small areas. [VERIFIED]

## 4. C1 and CTRL results

### 4.1 C1 (official, 2018-01 to 2021-12)
630 units (14 regions x 45 months: NOAA-20 estimates start in 2018-04, so there is no unit before it). Agree within the combined 90% interval: **615 of 630 = 97.6%** (Wilson 95%: 96.1% to 98.6%), PASS (threshold 85%). Overlapping intervals (more lenient): 629 of 630 = 99.8%. Median ratio S-NPP / NOAA-20: 1.001; median absolute log ratio 0.050; median |difference| = 0.38 combined sds. Per region the agreement is 88.9% (BONA) to 100% (eight regions); the median ratio by region runs from 0.96 (BOAS, BONA, CEAS, CEAM) to 1.11 (EQAS). With a minimum of 0 or 20 cell-days instead of 5 the result is 97.6% either way. [VERIFIED]

**In-sample status, stated plainly.** S-NPP's calibration fit is 2012-01 to 2016-12, so 2018-2021 is out of sample for S-NPP (its holdout). NOAA-20's calibration is 2018-04 to 2021-12, so every unit of the plan window is IN sample for NOAA-20: its ratios were fitted on exactly these months against Aqua. There is no month in the plan window that is out of sample for both. The official PASS is therefore partly by construction on the NOAA-20 side (both converted series are tied to Aqua in this period). The supplementary `C1-OUT-OF-SAMPLE-2022-2024` repeats the test on 2022-01 to 2024-04 (322 units, out of sample for both; it ends before the earliest VIIRS night drift onset, 2024-05): **98.4%** (317 of 322), PASS by the same threshold, which is outside the plan window and is not the official reading. [VERIFIED]

Limitation: the combined interval treats the two converted series as independent; both are expressed relative to Aqua, so their errors are not fully independent, and the interval of the difference is then somewhat too wide, which favours agreement. A median |difference| of 0.38 sd suggests the intervals are generous here. [HYPOTHESIS]

### 4.2 CTRL (official)
Both baselines exist for all 12 calendar months (same calendar month, 2003-2022).
| Window (25 months) | Harmonized ABOVE / BELOW / WITHIN / NO_ACT. / CANNOT | Aqua-only ABOVE / BELOW / WITHIN / NO_ACT. / CANNOT | Spurious |
|---|---|---|---:|
| 2011-01 to 2013-01 (around 2012-01) | 5 / 5 / 2 / 0 / 13 | 5 / 3 / 2 / 0 / 15 | **3** |
| 2017-04 to 2019-04 (around 2018-04) | 8 / 3 / 4 / 0 / 10 | 8 / 4 / 2 / 0 / 11 | 0 |

27 of the 50 months have a determinable harmonized verdict (the control had power); 21 harmonized ABOVE/BELOW verdicts, 3 of them spurious. The savanna has near-zero activity in the wet season, hence the many CANNOT_DETERMINE. **FAIL** by the rule fixed in advance (any spurious verdict). [VERIFIED]

| Month | Harmonized verdict (own baseline) | Aqua-only verdict (Aqua baseline) |
|---|---|---|
| 2011-03 | BELOW_NORMAL | CANNOT_DETERMINE |
| 2011-04 | BELOW_NORMAL | CANNOT_DETERMINE |
| 2012-09 | BELOW_NORMAL | CANNOT_DETERMINE |

### 4.3 Reading the three (diagnostic, no status)
`explain_months` gives the D-028 probabilities behind each verdict:
- **2011-03 and 2011-04** come before S-NPP exists: the harmonized estimate equals the Aqua-only estimate exactly (65 and 488 cell-days, same sd). The verdicts differ only because the two series use different baselines (the harmonized baseline, which includes the converted VIIRS years 2012-2022, gives p25 78.3 against 57.0 for the Aqua-measured one in March; p_below 0.838 against 0.276). These two are baseline effects, not an effect of the satellite change; the plan's rule as pre-registered counts them. [VERIFIED]
- **2012-09** (nine months after S-NPP enters): harmonized estimate 35,604 (sd 2,270), Aqua-only 37,936 (sd 3,406); p_below 0.898 for the harmonized series against 0.767 for the Aqua-only one, which falls just under the 0.8 line. The harmonized estimate is 6% below the Aqua-only one and its interval is narrower; the verdict flips because one probability crosses 0.8, not because of a step. [VERIFIED for the numbers; reading is a HYPOTHESIS]
- **Shared baseline** (`CTRL-SHARED-BASELINE`, both series against the Aqua-measured baseline, the form of D-029): the 2011 months agree, and two verdicts remain: 2012-09 (p_below 0.983 against 0.767) and 2017-10 (harmonized ABOVE with p_above 0.833, Aqua-only p_above 0.55; harmonized estimate 18,432 against 17,498). Also FAIL.

What is withdrawn or narrowed: the claim "no spurious verdicts at the satellite-change dates in a control region" is not supported by this test at the plan's strictness. The three cases are threshold crossings near 0.8 or baseline differences, not systematic ABOVE/BELOW runs after a change date, but the rule counts each. [VERIFIED for the count]

## 5. Choices the Lead must confirm ([ASSUMPTION]; details in the task prompt section 15)
1. B2 jump size: factor 1.5 to 3, up or down, log-uniform. A smaller range lowers detection, a larger one raises it.
2. B2 flag: `WITNESS_DISAGREEMENT` or a disagreement scale of at least 1.5 ("widened interval"); code-only reported as `B2-CODE-ONLY`.
3. B2 false flag: any flag in the unplanted twin's three months (official); monthly and per-series rates supplementary. Under pure chance the code fires in about 13% of three-month windows with two witnesses, so this reading is demanding.
4. B2 minimum data: at least 5 Aqua-equivalent cell-days in each of three months and a second witness.
5. C1: units with both estimates at least 5; agreement on the interval of the difference (the less lenient reading; overlap is supplementary); the in-sample status as in 4.1; the out-of-sample supplement uses 2022-01 to 2024-04.
6. CTRL: 25 months around each date (the plan lists 2011-01 to 2013-12 as the first analysis window; verdicts over the whole analysis windows are in the report: 3 spurious in 2011-01 to 2013-12, 0 in 2017-04 to 2019-04); each series against its own D-028 baseline (harmonized, and Aqua-measured); spurious = harmonized ABOVE/BELOW that the Aqua-only series does not give; INCONCLUSIVE below 12 determinable months.

## 6. Limitations
- One draw of 200 trials (seed 20261115); the Wilson intervals above say how far the rates could move with another seed. 89 distinct cells appear in the cell trials; trials in one region are not independent of each other.
- The planted jump multiplies the cell-days of one witness for the whole entity; real sensor faults can be partial (some cells, day only). The perturbation is in memory only; it is not an independent test of the calibration.
- B2 and CTRL use the v0.1 conversion (`0.1.0-combined-no-baseline`). If T-020c (v0.2) is adopted the tests re-run unchanged with the same command and the v0.1 results stay visible.
- C8 is one box, 720 cells; CTRL is a control, not a coverage test.

## 7. Re-run
```
mkdir data/interim/.heavy_lock            # the shared heavy-job lock; remove it when done
python pipeline/validation_b2_c1_ctrl.py all            # about 6 minutes; caches in data/interim/T-024
python pipeline/validation_b2_c1_ctrl.py ctrl           # or b2 / c1 alone, from the caches
python pipeline/validation_b2_c1_ctrl.py all --fresh    # recompute the aggregations
python -m pytest pipeline/tests/test_validation_b2_c1_ctrl.py -q -p no:cacheprovider
```
A second run gave the identical 200 trials and rates [VERIFIED].
