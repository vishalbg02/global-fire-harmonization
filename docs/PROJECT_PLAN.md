# Project Plan

Status labels used across `docs/`: **[VERIFIED date]** checked against a primary source · **[ESTIMATE]** derived from partial measurement · **[ASSUMPTION]** believed true, not yet checked · **[HYPOTHESIS]** to be tested · **[PROPOSED]** awaiting approval · **[APPROVED]** approved by the Project Lead.

## 1. Vision

The goal is a global platform that lets anyone see **how fire activity has changed anywhere on Earth since 2002**, and whether an apparent change reflects real fire activity or a change in the satellites observing it.

## 2. Problem statement

NASA FIRMS hotspot records come from several sensors whose detection ability differs and has changed over time:

| Sensor | Satellite | Start | End / status | Pixel |
|---|---|---|---|---|
| MODIS | Terra | Nov 2000 | Ending | ~1 km |
| MODIS | Aqua | Jul 2002 | Ending | ~1 km |
| VIIRS | S-NPP | Jan 2012 | Ended 2 Nov 2026 | 375 m |
| VIIRS | NOAA-20 | 2018 | Operating | 375 m |
| VIIRS | NOAA-21 | 2024 | Operating | 375 m |

Dates are from the FIRMS FAQ **[VERIFIED 2026-11-14]**.

- VIIRS detects far more small fires than MODIS.
- Terra and Aqua are drifting from their original overpass times.
- MODIS data collection ends in 2026–27. NASA sources disagree on the exact date.

Simply adding the records together produces artificial jumps and trends: more satellites, more detections. As a result, emergency managers, scientists and land managers cannot trust a raw hotspot calendar to tell them whether a month or year is unusual.

The challenge statement asks for a harmonized burning-activity calendar web app, built in two phases:
1. Harmonize so that "the sensor of origin no longer matters".
2. Build the application.

It also asks for area selection, current activity versus the historical median, accessible colour ramps and CSV download.

## 3. Proposed solution: *Many Witnesses + Witness Stand*

1. **Witnesses.** Aqua MODIS, S-NPP VIIRS and NOAA-20 VIIRS all pass in the early afternoon. Each one is converted to a common scale using calibration fitted on overlapping years, with explicit uncertainty.
2. **Combination.** Witnesses are weighted by their precision. Uncertainty is widened when they disagree. Adding a satellite therefore changes precision, not the level of the record.
3. **Verdicts.** Each month is classed as above normal, below normal, within normal or cannot determine, with probabilities, against a fixed baseline.
4. **Evidence panel.** For each result it shows whether the witnesses agree, how wide the uncertainty is, whether the data are sufficient, outages, and known caveats.
5. **Witness Stand.** A pre-registered validation suite across diverse fire regimes. Results are shown in the app, including failures.

The full method is in `SCIENTIFIC_METHODOLOGY.md`.

## 4. Target users

| User | Decision supported |
|---|---|
| Emergency managers / early warning | Is this month abnormal here? Should resources be pre-positioned? |
| Land / protected-area managers | Is the local fire regime changing? |
| Scientists | Can a 2002–present hotspot series be used without sensor-related jumps? |
| Policy / journalists | Did burning actually change, or did the observation change? |

## 5. Global scope **[APPROVED 2026-11-14, D-002]**

- Coverage is worldwide on a regular analysis grid, with country, continent and custom-area aggregation.
- **"Explore anywhere" ≠ "a verdict everywhere".** Cells and areas without enough data show "no detected activity" or "cannot determine". Coverage (the % of land area with a determinable verdict) is reported.
- Custom areas are approximated by the analysis-grid cells they contain. The app states this.
- Validation covers sampled events and regions. We make **no claim of global accuracy**.

## 6. Features and priorities **[PROPOSED]**

| # | Feature | Priority | Feasibility note |
|---|---|---|---|
| F1 | Global map of the selected month (verdict / raw / harmonized layers) | **MVP** | Precomputed per month; analysis grid |
| F2 | Country and continent selection | **MVP** | Each detection's country comes from the FIRMS file name; boundaries come from Natural Earth |
| F3 | Custom area: rectangle | **MVP** | API aggregates the cells inside it |
| F3b | Custom area: free polygon | P1 | Drawing tool plus point-in-polygon on cells |
| F4 | Historical calendar (years × months, % of normal or activity) | **MVP** | Accessible colour ramps |
| F5 | Raw vs harmonized toggle | **MVP** | The core demo interaction |
| F6 | Verdicts with probabilities | **MVP** | Four outcomes plus "no detected activity" |
| F7 | Satellite witness comparison and observation-effort info | **MVP (simple)** | Per-witness series, satellite timeline, outage months |
| F8 | Evidence and uncertainty panel | **MVP** | Reason codes from the data contract |
| F9 | Global anomaly overview (ranked countries/cells) | **MVP (simple list)** | Sort entities by probability above normal |
| F10 | CSV export of monthly series | **MVP** | Raw points: link to FIRMS (too large) |
| F11 | Methodology and validation results page | **MVP** | Rendered from `validation_results.json` |
| F12 | Large-fire consistency check | P1 | Diagnostic, not a correction |
| F13 | "MODIS blindness" indicator | P1 | Falls out of the calibration step |
| F14 | Public deployment | P1 | Local demo plus recorded video is the primary artifact |
| F15 | Day/night timing-shift warning | P2 | Confounded by drift |
| F16 | NOAA-21, Terra harmonization, burned-area corroboration | P2 / cut | See `DECISION_LOG.md` |

**Cut first if time is short, in this order:** F14 → F12 → F3b → validation test E → F13. MVP items are cut only by an explicit Project Lead decision.

## 7. Deliverables

1. A harmonized global dataset and products conforming to `DATA_CONTRACT.md` (Member 2).
2. The web application implementing the MVP features (Member 3).
3. Witness Stand results with actual pass/fail outcomes (Member 2, reviewed by Member 1).
4. Methodology and limitations documentation (Member 2 and Member 1).
5. A demo video with English subtitles, the Space Apps project page and the submission (Member 1).

## 8. Milestones and gates (H0 = stack approval)

| Gate | Hour | Criterion | If it fails |
|---|---|---|---|
| G0 | H1 | Downloads and 2026 API pulls running; stack and contract approved | Lead unblocks immediately |
| G1 | H8 | Global cell-month tables per witness exist; raw sensor jump visible; grid, baseline and validation thresholds **locked** | Coarser grid; process fewer years in parallel |
| G2 | H16 | Calibration plus holdout done; app renders fixture data end-to-end through the API | Fallback A (fixed regional ratios) |
| G3 | H26 | Verdicts produced globally; validation tests run; app on real data | Fallback B (sequential witnesses) |
| Freeze | H28 | No new features | — |
| Submit | H34 | Submission complete, links checked | H34–36 reserve |

## 9. 36-hour schedule (three people)

**Assumptions:**
- H0 is the moment the stack is approved.
- The Space Apps submission closes **15 Nov 2026, 23:59 local time** **[VERIFIED 2026-11-14, submission guide]**.
- People sleep in staggered shifts.

| Hours | Member 1: Lead | Member 2: Data and science | Member 3: App and UI |
|---|---|---|---|
| H0–1 | Approve stack and contract; confirm deadline; add collaborators | **Start archive downloads + 2026 API pulls** (T-001, T-002) | Environment setup per approved stack (T-030) |
| H1–4 | Finalize validation event windows and bounding boxes (T-050); check the GFED region-mask source (T-004) | Produce **SYNTHETIC fixtures** per the contract (T-010); unzip and normalize (T-003) | Map shell and country layer using fixtures (T-031) |
| H4–8 | Draft the demo storyline (T-060); review fixtures against the contract | Global cleaning, gridding, cell-month tables per witness (T-005, T-006) | Calendar and toggle on fixtures (T-032, T-033) |
| **H7–8** | **Review R1:** data quality and raw-jump check; sign off **G1** locks (T-051) | Present the G1 evidence | API skeleton serving fixtures (T-034) |
| H8–13 | Write the methods page draft from the methodology document | Calibration with pooling and holdout (T-011, T-012) | Area selection; rectangle custom area via API on fixtures (T-035) |
| **H13–14** | **Review R2:** calibration plausibility; app renders fixtures end-to-end → **G2** (H16 at the latest) | Present calibration and holdout numbers | Demo the fixture-driven app |
| H14–18 | **Sleep** | **Sleep** | Evidence panel, witness chart (T-036, T-037) |
| H18–19 | Review the anomaly-list wording | Combination, verdicts, entity aggregation (T-013, T-014) | **Sleep (H18–22)** |
| H19–23 | **Sleep** | (continues T-013/T-014) | (sleeping) |
| H22–25 | Draft the project page | Run validation tests (T-020 to T-025) | Integrate real products; CSV export (T-038, T-039) |
| **H25–26** | **Review R3:** validation results (honest pass/fail) and app on real data → **G3** | Present results, including failures | Present the app on real data |
| H26–28 | Follow up on R3 issues | Write actual results into `VALIDATION_PLAN.md`; fixes | Anomaly list; methods/validation page (T-040, T-041) |
| **H28** | **Feature freeze** | | |
| H28–30 | Storyboard final; start recording | Verify every number shown in the app against products (T-026) | Performance, accessibility (T-042) |
| **H30–31** | **Review R4:** final review of both workstreams | Methodology limits; then **sleep H31–33** | Static fallback build; optional deploy (T-043) |
| H31–32 | Record the demo; subtitles; project page (T-061, T-062) | (sleeping) | Bug fixes only |
| H32–34 | **Submit** (T-063); verify links | Buffer | Buffer |
| H34–36 | Reserve | Reserve | Reserve |

The critical path runs through Member 2: download → grid → calibrate → verdicts → validation. The Lead shields Member 2 from all non-essential work.

## 10. Risks and fallbacks

See `RISKS_AND_LIMITATIONS.md`. The two main fallbacks:
- **Fallback A:** fixed fire-region × season × day/night conversion ratios without local pooling.
- **Fallback B:** no combination step. Aqua is used through 2021, then converted S-NPP, then converted NOAA-20 after 2 Nov 2026. Other witnesses are shown as cross-checks only.
