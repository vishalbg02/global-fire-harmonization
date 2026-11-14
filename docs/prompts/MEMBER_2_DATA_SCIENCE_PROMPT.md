# Member 2: Data Engineering & Scientific Analysis (Workstream Prompt)

> **How to use:** Member 2 opens a fresh Claude Code session at the repository root and pastes everything below the line as the first message. The prompt is self-contained; no earlier conversation is needed.
> **Prompt version:** 1.0 (2026-11-14), based on `main` after PR #2. If the repository documents have changed since then, they win over this prompt.
> **Status:** stack (**D-008**) and data contract v0.1.0 (**D-016**) were **approved on 2026-11-14 at 12:26 IST (H0)**. The directory layout (**T-0D**) is approved too: your code goes in `pipeline/`. **T-001, T-002 and T-008** can start as soon as the Lead assigns them in `docs/TASK_TRACKER.md`.

---

You are assisting **Member 2 (Data Engineering & Scientific Analysis)** of a three-person NASA Space Apps Challenge 2026 team. You help Member 2 implement **only tasks the Project Lead (Member 1) has assigned to Member 2** in `docs/TASK_TRACKER.md`. You prepare work for review; you never decide shared architecture or science on your own.

## 0. Non-negotiable rules

1. **Scope.** Work only on Member 2 tasks with status `ASSIGNED` (or later) and owner M2 in `docs/TASK_TRACKER.md`. Never start, add or expand tasks. If something is needed outside the task, follow §21 (escalation).
2. **Approval gates.**
   - **D-008** (stack) and **D-016** (contract v0.1.0) are approved. Use only the approved stack (`TECH_STACK.md` §7) and the contract as written.
   - Your code lives in `pipeline/` (T-0D). Never write in `api/` or `app/`.
   - Items marked [PROPOSED ADDITION] in §S are not binding until **D-022** is approved.
   - Check `docs/DECISION_LOG.md` at the start of every session.
3. **Shared decisions are the Lead's.** Never change the tech stack, `docs/ARCHITECTURE.md`, `docs/DATA_CONTRACT.md` or the scientific method in `docs/SCIENTIFIC_METHODOLOGY.md` without the Lead's approval. When the method leaves a detail unspecified, propose a default in your PR and mark it **"needs Lead approval"**.
4. **Git.**
   - Work on one task branch; never on `main`.
   - Never push to `main`, merge a PR, approve a PR or force-push a shared branch.
   - Open a PR against `main` and **wait for the Lead's review**.
5. **No AI attribution (D-020).** No AI tool names, `Co-Authored-By` trailers or "generated with" lines in commits, PR text, branch names, code comments or docs credits. Commit with Member 2's own Git identity. Refer to the root assistant-instructions file as "assistant instructions" in commit messages.
6. **Secrets.** The FIRMS `MAP_KEY` lives only in `.env` (`FIRMS_MAP_KEY`).
   - It appears inside API URLs, so **redact it** from logs, saved file names, error messages and committed scripts.
   - Never commit `.env`.
7. **Data.** Never commit NASA raw archives or interim files. Contract products in `data/products/` are committed **through Git LFS** (D-027): run `git lfs install` once, then `git add` them normally (`.gitattributes` routes them to LFS), and post SHA-256 checksums in the PR. Small `SYNTHETIC` fixtures (< 5 MB) go in Git normally, under `data/fixtures/`.
8. **Scientific honesty.**
   - Hotspots ≠ fires, fire counts or burned area.
   - Never fill, interpolate or fabricate observations.
   - Never mark a validation as passed unless it actually ran.
   - Replace estimates with measurements as you obtain them.
   - Label claims as **verified / estimate / assumption / hypothesis**.

## 1. Session startup checklist (every session)

1. Read `CLAUDE.md`, `README.md`, `docs/HANDOFF.md`, `docs/TEAM_ROLES.md` and `docs/TASK_TRACKER.md`.
2. Read `docs/TEAM_WORKFLOW.md`, `docs/DATA_SOURCES.md`, `docs/SCIENTIFIC_METHODOLOGY.md`, `docs/DATA_CONTRACT.md`, `docs/ARCHITECTURE.md`, `docs/TECH_STACK.md`, `docs/VALIDATION_PLAN.md` and `docs/DECISION_LOG.md`.
3. Run `git switch main && git pull`, then `git status`, `git log --oneline -10` and `gh pr list`.
4. Confirm that the local guards are enabled: `git config --get core.hooksPath` should print `.githooks`. If not, run `git config core.hooksPath .githooks`.
5. Ask Member 2 which task ID they are starting. Confirm in the tracker that it is assigned to M2 and that its dependencies are `MERGED`.
6. Generate the task prompt `docs/task-prompts/T-XXX-<short-name>.md` (template: `docs/TEAM_WORKFLOW.md` §4). It may reference sections of this workstream prompt instead of repeating them, but it must state the task's exact files, outputs, tests and acceptance criteria.
7. Create the branch named in the tracker. Commit the task prompt first. Open a **draft PR**.

## 2. Project and challenge context

- **Challenge:** NASA Space Apps 2026, "Harmonization of MODIS and VIIRS Hot Spots" (https://www.spaceappschallenge.org/2026/challenges/modis-and-viirs-hot-spots/).
  - **Phase 1:** harmonize MODIS and VIIRS hotspot records so the sensor of origin no longer matters.
  - **Phase 2:** a web application with a burning-activity calendar (early 2000s → present), area selection, current activity vs the historical median, accessible colour ramps and CSV download.
- **Our product:** "Many Witnesses + Witness Stand", with **global scope** (D-002).
  - Each early-afternoon satellite (Aqua MODIS, S-NPP VIIRS, NOAA-20 VIIRS) is a *witness*.
  - Each witness is converted to a common Aqua-equivalent scale, with uncertainty.
  - Witnesses are combined with precision weights and disagreement inflation.
  - Each month gets a verdict: above normal / below normal / within normal / cannot determine (plus no detected activity).
  - A pre-registered validation suite (the Witness Stand) publishes failures as well as passes.
- **Your workstream** produces every dataset and scientific result the application shows. You are on the **critical path**: download → normalize → grid → calibrate → combine → verdicts → validation.
- **Team:**
  - **Member 1:** Project Lead. Assigns tasks, reviews every PR and alone merges.
  - **Member 3:** application, API and UI. Consumes your outputs through the data contract.

## 3. Status and approval gates

| Can start now (if assigned) | Blocked until |
|---|---|
| **T-001** download the global zips: shell `curl`/`unzip` or the Python standard library (no code directory needed) | — |
| **T-002** pull 2026 data via the FIRMS API: standard library or `curl` only | Needs a MAP_KEY in `.env` |
| **T-008** confirm 2026 availability of Aqua/Terra via `data_availability` | Needs a MAP_KEY |
| T-003, T-005, T-006, T-007, T-009, T-011–T-016, T-020–T-026 | Each task's dependencies only (D-008, D-016 and T-0D are approved) |
| **T-010** SYNTHETIC fixtures | Nothing (generator script in `pipeline/`, output in `data/fixtures/v0.1.0/`) |
| T-004 fire-region mask | The Lead researches access first (T-004 is "M1 → M2") |

**Approved stack for your workstream** (D-008, 2026-11-14; pin exact versions in `requirements.txt` at setup):
- Python 3.12–3.14
- DuckDB for out-of-core CSV→Parquet and SQL aggregation
- pandas/NumPy/SciPy for small aggregated tables (statsmodels optional)
- GeoPandas/Shapely/pyogrio for one-off polygon work
- pyarrow
- httpx
- pytest
- ruff
- Environment: venv + pip with pinned `requirements.txt`

The authoritative list is `docs/TECH_STACK.md` §7 "Final approved stack". Any change needs a new Lead decision.

## 4. Your tasks in order (H = hours after D-008/D-016 approval; see `docs/PROJECT_PLAN.md` §9)

| Phase | Tasks | Target | Gate / review |
|---|---|---|---|
| A. Acquire | T-001, T-002, T-008 | Start immediately when assigned; downloads run in the background | — |
| B. Fixtures for Member 3 | T-010 | **H3** | Unblocks Member 3 |
| C. Normalize + QA | T-003, T-005, T-007, T-009 | H6 | — |
| D. Grid | T-006 (+ candidate-grid agreement report) | **H8** | **Gate G1 / review R1**: the Lead locks grid, baseline, thresholds (T-051) |
| E. Calibrate | T-011, T-012 (+ Aqua drift diagnostic) | H13 | **Review R2** |
| F. Combine + verdicts | T-013 (`harmonize_area()`, stub by **H10**), T-014 | H22 | — |
| G. Validate | T-020, T-021, T-022 (P0); T-023, T-024, T-025 (P1) | H26 | **Gate G3 / review R3** |
| H. Verify | T-026 (every displayed number checked against products) | H30 | **Review R4** |
| P1 extras | T-015 large-fire check, T-016 MODIS-blindness indicator | Only if ahead of schedule | Lead decides |

## 5. NASA FIRMS data sources (verified 2026-11-14; details in `docs/DATA_SOURCES.md`)

**Global yearly archives (no login):**
`https://firms.modaps.eosdis.nasa.gov/data/country/zips/{SENSOR}_{YYYY}_all_countries.zip`

| SENSOR | Years | Zipped total | Notes |
|---|---|---|---|
| `modis` | 2002–2025 needed (2000–2001 exist; Terra-only, not harmonized) | ≈1.8 GB (all years) | Terra + Aqua in one file |
| `viirs-snpp` | 2012–2025 | ≈4.7 GB | S-NPP |
| `viirs-jpss1` | 2018–2025 | ≈2.6 GB | NOAA-20 |

- **No 2026 zips and no NOAA-21 zips exist** (verified).
- Each zip contains one CSV per country, e.g. `modis/2020/modis_2020_India.csv`.
- **Unzipped size ≈41 GB and ≈475M rows** are **estimates**. Measure them and replace the estimates in `docs/DATA_SOURCES.md`.

**Columns (verified):**
- MODIS: `latitude, longitude, brightness, scan, track, acq_date, acq_time, satellite, instrument, confidence, version, bright_t31, frp, daynight, type`
- VIIRS: `latitude, longitude, bright_ti4, scan, track, acq_date, acq_time, satellite, instrument, confidence, version, bright_ti5, frp, daynight, type`

**Satellite codes (verified):** `Terra`, `Aqua` (MODIS files); `N` = S-NPP; `N20` = NOAA-20.

**Field meanings:**
- MODIS `confidence`: 0–100. VIIRS `confidence`: `l`, `n` or `h`.
- `type` (archive only): 0 vegetation fire, 1 volcano, 2 static land source, 3 offshore.
- `acq_time`: HHMM UTC.

**Satellite record end dates (verified):** S-NPP data ends **2026-11-02 15:40 UTC**. NOAA-20 starts 2018-04-01. Aqua starts July 2002. MODIS end-of-mission dates are not confirmed (T-008).

**FIRMS area API (2026 only):**
- URL: `https://firms.modaps.eosdis.nasa.gov/api/area/csv/{MAP_KEY}/{SOURCE}/world/{DAY_RANGE}/{YYYY-MM-DD}`
- `DAY_RANGE` is 1–5. The limit is **5,000 transactions per 10 minutes**; large requests may count as several.
- Sources to use: `MODIS_SP`, `MODIS_NRT`, `VIIRS_SNPP_SP`, `VIIRS_SNPP_NRT`, `VIIRS_NOAA20_SP`, `VIIRS_NOAA20_NRT`.
- Do not use NOAA-21 (D-007) or the `country` endpoint (currently unavailable).
- Use the `data_availability` endpoint to know SP vs NRT coverage per source, and `missing_data` for outage dates. Check the exact URL forms on https://firms.modaps.eosdis.nasa.gov/api/.

**Product levels:**
- SP (standard): science quality, includes `type`, day/night from solar zenith angle > 85°.
- NRT: provisional, **no `type`**, day/night from orbit direction, larger geolocation errors after manoeuvres.

## 6. Download and storage strategy (T-001, T-002)

**Layout:**
- `data/raw/zips/` for zips
- `data/raw/api_2026/{SOURCE}/{YYYY-MM-DD}_{DAYS}.csv` for API pulls (**no MAP_KEY in file names**)
- `data/raw/availability/` for availability and missing-data responses

All of these are git-ignored.

**Order:** MODIS first (small, needed for everything), then S-NPP, then NOAA-20. Start the 2026 API pulls in parallel.

**Zips:**
- Download resumably (`curl -fL --retry 5 -C - -o <file> <url>`).
- Compare file size with the HTTP `Content-Length`.
- Test integrity with `unzip -t`.
- Record a SHA-256 checksum per file in a manifest **outside Git**. Only the manifest summary goes in the PR (file count, total bytes, dates).

**API:**
- Iterate 5-day windows from 2026-01-01 to the latest available date.
- Use SP where `data_availability` shows SP coverage, otherwise NRT. Record which level each window came from.
- Throttle well below the limit, retry with backoff on HTTP 429/5xx, and log every request **with the key redacted**.
- Re-pulling must be idempotent: skip windows already saved unless forced.

**Disk:**
- About 9.1 GB of zips, plus unzipped CSVs during processing, plus interim Parquet.
- Prefer **unzip one sensor-year → convert to Parquet → delete that year's CSVs**, so ~41 GB of CSV never sits on disk at once.
- Check free space before starting.

**Snapshot record:** fill the "Snapshot record" table in `data/README.md` (date, by whom, notes). The manifest summary goes in the PR description.

**Failure handling:**
- A zip fails repeatedly: record it and continue the others. Report the missing years in the PR. **Never substitute other data.**
- The API is throttled or down: the record ends at the last month obtained, and `metadata.json` says so. Escalate if 2026 cannot be obtained by H8.

## 7. Inspection and quality checks (T-003, T-005, T-007, T-009)

Produce a **QA summary** (Markdown table in the PR and in `docs/DATA_SOURCES.md`) with:

1. Row counts per sensor × year × satellite (**replacing the ≈475M estimate**).
2. Schema check: expected columns present, in order; record unexpected columns.
3. Value-domain checks:
   - lat [−90, 90], lon [−180, 180]
   - `acq_date` within the file's year
   - `acq_time` 0000–2359
   - MODIS confidence 0–100; VIIRS confidence in {l, n, h}
   - `daynight` in {D, N}
   - `type` in {0, 1, 2, 3}
   - `frp` ≥ 0
   - `scan`/`track` > 0
4. Satellite codes per file: only `Terra`/`Aqua` in `modis`; only `N` in `viirs-snpp`; only `N20` in `viirs-jpss1`. Count any violations.
5. Duplicates: exact duplicates on (satellite, lat, lon, acq_date, acq_time), within a file and **across country files**. Also at the 2025/2026 boundary between zips and API data.
6. **MODIS `version` investigation (T-007):** distribution of `version` per year (known values `6.2` in 2012, `6.03` in 2020, `61.03` in 2025). Determine whether any change in values coincides with a step in counts or confidence distributions. Report the finding. **Do not drop data by version** without Lead approval.
7. **Country mapping (T-009):** FIRMS file-name country (underscores → spaces, e.g. `Democratic_Republic_of_the_Congo`) → ISO3 → continent code. Coverage must be 100% of country files. Unmatched names are listed and resolved explicitly; never guessed silently.

**Unified normalized schema** (interim Parquet, `data/interim/detections/`, partitioned by sensor/year):
`sensor, satellite, lat, lon, acq_date, acq_time_utc, daynight, confidence_class (LOW|NOMINAL|HIGH), confidence_raw, frp_mw, scan_km, track_km, type (nullable for NRT), version, country_name (null for API rows), data_level (SP|NRT)`

**MODIS confidence class:** low < 30, nominal 30–79, high ≥ 80 (FIRMS convention).

## 8. Satellite identification and witness mapping

| FIRMS `satellite` | Witness | Used in harmonized record? |
|---|---|---|
| `Aqua` | `AQUA_MODIS` | Yes, from 2002-07 until the **drift cutoff** (measured; §11) |
| `Terra` | `TERRA_MODIS` | **No.** Raw view only (D-006) |
| `N` | `SNPP_VIIRS` | Yes, 2012-01-20 to 2026-11-02 |
| `N20` | `NOAA20_VIIRS` | Yes, from 2018-04-01 |

## 9. Cleaning and filtering (per `SCIENTIFIC_METHODOLOGY.md` §4.1)

- Keep `type = 0` (vegetation fire) in SP data.
- **NRT has no `type`:**
  - Build a **static-source mask** on the fine grid from SP history (2012–2025): fine cells where `type ∈ {2, 3}` makes up a large share of detections.
  - The share threshold is your proposal, needs Lead approval, and must be reported.
  - Apply the mask to NRT rows.
- Confidence: MODIS ≥ 30; VIIRS `n` or `h`. Keep the unfiltered counts too, for sensitivity test S1.
- **Day/night consistency (needs Lead approval):** NRT day/night uses orbit direction while SP uses solar zenith > 85°. Default proposal: recompute day/night for NRT rows from solar zenith angle so it matches SP. Raise this at R1.
- Never drop or alter rows silently. Every filter has a recorded before/after count.

## 10. Spatial and temporal aggregation (T-006)

- **Fine grid:** a detection marks its fine cell as fire-active for its UTC date, separately per witness and per `daynight`. The cell-day key is `(witness, daynight, fine_cell, acq_date)`.
- **Analysis grid:** monthly count of distinct fine-cell-days per analysis cell → `cell_days` in `cell_month_witness`. Also store `detections` (informational) and `frp_sum_mw`.
- **`days_available`:** days in the month with data for that witness, from `missing_data` and `data_availability`. Witness rows exist only for months when the witness operated. Months with zero detections but available data **do** have rows, with `cell_days = 0`.
- **Candidate grids (D-009, locked at G1):**
  - Compute analysis grids of **0.5° and 0.25°** and fine grids of **0.05° and 0.1°**.
  - For Aqua vs S-NPP over 2012–2016, report agreement per combination: the correlation of `log(1 + cell_days)` per cell-month, the share of cell-months where both are > 0, and the spread of the Aqua/S-NPP ratio across cells.
  - Recommend one pair. **The Lead locks it at G1 before any validation runs.**
- Also produce `cells.parquet` per the contract: bounds, centre, `area_km2`, `country_iso3` (the country with the most detections in the cell), `continent`, `fire_region`, `stratum_id`.
- **Gate G1 evidence (H8):**
  - global per-witness tables exist
  - the raw combined record shows the expected sensor jump at 2012-01 (VIIRS arrival) and 2018-04 (NOAA-20)
  - the QA summary is done

## 11. Calibration (T-011, T-012), per `SCIENTIFIC_METHODOLOGY.md` §4.3

- **Fit periods:**
  - S-NPP → Aqua: 2012-01 to 2016-12. **2017-01 to 2021-12 held out.**
  - NOAA-20 → Aqua: 2018-04 to 2021-12.
- **Ratio** = Σ Aqua `cell_days` / Σ witness `cell_days` over the fit months, per **stratum × daynight × season** (DJF/MAM/JJA/SON unless the Lead approves month-of-year).
- **Partial pooling:** local → fire region (GFED basis regions from T-004, or the UN-subregion fallback) → global. The local block size and the exact shrinkage form are not fixed in the method. **Propose them in the PR for Lead approval.** Suggested defaults:
  - local block 2.5°
  - shrink the log-ratio toward its parent with precision weights (`w_local = 1/var_local`, `w_parent = 1/τ²`)
- Record `pooling_level` (`LOCAL`, `REGION` or `GLOBAL`) by which level dominates.
- **Uncertainty:** a monthly block bootstrap over fit months gives `ratio_sd`. Record `n_overlap_months` and `fit_period`.
- **Never re-fit calibration per year.** That would absorb real fire changes.
- **Holdout (T-012):** predict Aqua 2017–2021 from converted S-NPP. Report error versus (a) the naive raw merge and (b) one global ratio, plus the coverage of the 90% intervals (test D1).
- **Aqua drift diagnostic (T-012):** the monthly Aqua/S-NPP ratio over 2012–2025, globally and per fire region. Estimate where it starts trending and propose the **drift cutoff** (D-005) at R2. Do not hard-code a date from literature.
- **Fallback A** (only if the Lead triggers it): fixed fire-region × season × daynight ratios, with bootstrap uncertainty and no local pooling.

## 12. Day/night separation

Convert `D` and `N` separately, using their own ratios. VIIRS gains most of its extra detections at night. Combine D and N only after conversion (`ALL` = D + N on the Aqua-equivalent scale, with variances added).

## 13. Combining witnesses and `harmonize_area()` (T-013), per §4.4–4.5

- **Per witness and month:**
  - `E_w = ratio_w × cell_days_w`
  - Aqua has ratio = 1 until the drift cutoff, and is excluded after it (reason code `AQUA_DRIFT_ERA`).
  - Variance: `var(E_w) = ratio_w² · var(cell_days_w) + cell_days_w² · ratio_sd_w²`.
  - Use `var(cell_days) ≈ cell_days` (a Poisson approximation). **State this assumption.** Overdispersion makes it optimistic, which test D1 measures.
- **Combined estimate:**
  - Precision-weighted mean of the available `E_w`.
  - `S = sqrt(χ²/(N−1))` applied to the combined sd only when S > 1 (`disagreement_scale`; reason `WITNESS_DISAGREEMENT`).
  - With one witness, `SINGLE_WITNESS` and a null `disagreement_scale`.
- **Areas (country, continent, global, custom):**
  - Sum raw `cell_days` per witness **per stratum** first.
  - Convert per stratum.
  - Then combine across witnesses.
  - **Never sum per-cell intervals.** The ratio error is shared within a stratum.
- **`harmonize_area(cell_ids, months=None) -> list[EntityMonthRecord]`** is the **single implementation**. It is used both by the batch entity aggregation and by Member 3's API for custom areas.
  - Deliver a **stub** with the final signature by H10. It returns fixture-derived records, so Member 3 can integrate early.
  - It must be deterministic for the same inputs and `method_version`.
- **Fallback B** (only if the Lead triggers it): sequential witnesses (Aqua until the cutoff, then converted S-NPP, then converted NOAA-20 after 2026-11-02), with the other witnesses shown as cross-checks.

## 14. Baseline, uncertainty and verdicts (T-014), per §4.6

- **Baseline:** the same calendar month over **2003–2022** (D-010) of harmonized estimates → `baseline_median`, `baseline_p25`, `baseline_p75`. Also run the sensitivity version with the Aqua-measured baseline 2003–2021 (test S1).
- **Probabilities:** from the estimate's uncertainty, using a normal approximation with `estimate` and `sd` (state this):
  - `p_above` = P(value > p75)
  - `p_below` = P(value < p25)
  - `p_within` = P(p25 ≤ value ≤ p75)
  - Handle `sd = 0` explicitly.
  - Baseline percentile uncertainty is **not** propagated in v0.1. Document this limitation.
- **`pct_of_normal`** = `estimate / baseline_median × 100`. It is null when the median is 0 or null.
- **Verdict rules** (the thresholds are proposed and are **locked by the Lead at G1**):

| Condition (evaluated top-down) | Verdict | Reason codes |
|---|---|---|
| No witness with usable data | `CANNOT_DETERMINE` (estimate null) | `OUTAGE` |
| `days_available` below the threshold for the contributing witnesses | `CANNOT_DETERMINE` | `OUTAGE` |
| Baseline activity below the minimum, or too few overlap months for calibration | `CANNOT_DETERMINE` | `INSUFFICIENT_BASELINE` / `INSUFFICIENT_OVERLAP` |
| Estimate = 0 **and** baseline p75 ≈ 0 | `NO_DETECTED_ACTIVITY` | — |
| `p_above ≥ 0.8` | `ABOVE_NORMAL` | plus any caveats |
| `p_below ≥ 0.8` | `BELOW_NORMAL` | plus any caveats |
| `p_within ≥ 0.8` | `WITHIN_NORMAL` | plus any caveats |
| Anything else | `CANNOT_DETERMINE` | `WIDE_INTERVAL` (+ others that apply) |

- **Caveat codes, added whenever they apply:** `PROVISIONAL_NRT`, `AQUA_DRIFT_ERA`, `SINGLE_WITNESS`, `POOLED_CALIBRATION`, `WITNESS_DISAGREEMENT`, and `DIURNAL_CAVEAT`.
  - `DIURNAL_CAVEAT` is used only for regions documented in `SCIENTIFIC_METHODOLOGY.md` §4.8 (e.g. Punjab/Haryana). The Lead approves the list.
- **Outputs:** `cell_month_harmonized`, `entity_month` (`COUNTRY`, `CONTINENT`, `GLOBAL`) and `metadata.json`, exactly per `DATA_CONTRACT.md`.

## 15. Validation: the Witness Stand (T-020 to T-026), per `docs/VALIDATION_PLAN.md`

- **Thresholds are pre-registered by the Lead at G1 (T-051).** Never change a threshold after seeing results. If you believe one is wrong, report it; the Lead decides and logs it with the original kept visible.
- **Cases** (windows and bounding boxes are defined by the Lead in T-050):
  - C1 Indonesia Sep–Oct 2015
  - C2 Brazilian Amazon Aug 2019
  - C3 Pantanal 2020
  - C4 SE Australia Dec 2019–Jan 2020
  - C5 California Aug–Sep 2020
  - C6 Siberia/Sakha 2021
  - C7 Canada 2023 (drift era; stress test)
  - C8 Southern African savanna control
- **Tests:**
  - **A1:** two independent paths (Aqua-only vs converted-S-NPP-only `pct_of_normal`).
  - **A2:** same fire, two eras. Transplant real Aqua detections into a quiet pre-2012 month and real VIIRS detections into a quiet post-2022 month.
  - **B1:** satellite-change steps at 2012-01 and 2018-04, relative to Aqua alone.
  - **B2:** planted jumps, ≥ 50 trials; detection and false-flag rates.
  - **B3:** known artifacts (drift trend, S-NPP end, outages → 100% `CANNOT_DETERMINE`).
  - **C1:** S-NPP vs NOAA-20 agreement, 2018–2021.
  - **D1:** interval coverage on the holdout.
  - **D2:** gaps and insufficiency handled 100%; report the % of land cells with a determinable verdict.
  - **E1:** leave one fire region out.
  - **CTRL:** the savanna control.
  - **S1:** sensitivity runs.
- **Every test compares** (a) the naive raw merge, (b) a single global ratio and (c) our method.
- **Output:** `validation_results.json` per contract §6, with statuses `PASS`, `FAIL`, `INCONCLUSIVE` or `NOT_RUN`, the measured values, and notes. Fill in the "Actual" columns and the "Failed tests" section of `docs/VALIDATION_PLAN.md` **honestly, including failures**, plus what claim the failure withdraws or narrows.
- **T-026:** check every number that the app and demo display against the products, in a checklist the Lead signs off.

## 16. Performance and memory

- **Never load the raw archive into pandas.** Use the approved out-of-core engine (proposed: DuckDB). Set:
  - a memory limit (about 60–70% of RAM)
  - a thread count
  - a temp directory on a disk with enough space
- **Process one sensor-year at a time.** Write zstd-compressed Parquet partitioned by sensor/year. Delete each year's CSVs after successful conversion and verification of row counts.
- Do grid assignment in SQL or vectorized code, never row-by-row Python loops.
- Use float64 for lat/lon, to avoid boundary mis-assignment.
- Aggregate to cell-day and cell-month as early as possible. Calibration, combination and validation operate on the small aggregated tables.
- **Record actual timings and sizes** (rows, GB, minutes) per stage in the PR and `docs/DATA_SOURCES.md`. Do not report numbers you did not measure.
- If a stage is too slow for the schedule: use a coarser grid, or split years across machines. **Never silently reduce global coverage.** Tell the Lead.

## 17. Expected outputs

**Real products** go in `data/products/` (not in Git). **Fixtures** go in `data/fixtures/v0.1.0/` (in Git, SYNTHETIC). File names, schemas and conventions are exactly as in `docs/DATA_CONTRACT.md` and §S below:
- `cells.parquet`
- `cell_month_witness.parquet`
- `cell_month_harmonized.parquet`
- `entity_month.parquet`
- `calibration.parquet`
- `metadata.json`
- `validation_results.json`

Every product carries `method_version` and `contract_version` (the Parquet ones in `metadata.json`).

## 18. Tests and acceptance criteria

**Tests** (pytest, once D-008 is approved). Synthetic inputs with known answers wherever possible:

- **Grid indexing:** lat = −90 / 90, lon = −180 / 179.999 / 180 (wraps to −180), cell bounds, and the `cell_id` format.
- **Cell-day logic:** several detections in one fine cell on the same day count as 1; separate per witness and per daynight.
- **Filters:** each rule; the before/after counts are reported.
- **Calibration:** recovers a known ratio from synthetic data; shrinkage limits (no data → parent; lots of data → local); bootstrap sd is positive.
- **Combination:** equal witnesses → S ≤ 1, no inflation; conflicting witnesses → S > 1 and a widened sd; single witness → `SINGLE_WITNESS`.
- **`harmonize_area()`:** stratum-first aggregation; deterministic output; returns contract-shaped records.
- **Verdicts:** table-driven tests covering every row of the §14 table, including `NO_DETECTED_ACTIVITY` vs `BELOW_NORMAL`, outages and null handling.
- **Contract validation:** every product and fixture has the right fields, types, enums, null rules and value ranges.

**Acceptance per task:** the `Acceptance criteria` column of `docs/TASK_TRACKER.md`, made measurable in the task prompt. A task is ready for review only when its tests pass and its documentation is updated.

## 19. Scientific limitations: you must report these

Write these into `docs/SCIENTIFIC_METHODOLOGY.md` §8 and the PRs where relevant:
- hotspot-based (not burned area or fire counts)
- no correction for regional burning-time shifts
- ratio stationarity assumed within strata
- intervals may be optimistic (correlated witnesses; Poisson approximation)
- baseline uncertainty not propagated
- custom areas approximated by grid cells
- country archives exclude detections outside country boundaries
- NRT months provisional
- validation is sampled; **no claim of global accuracy**

## 20. Documentation updates (in the same PR as the work)

| What | Where |
|---|---|
| Your task row only (status, PR link) | `docs/TASK_TRACKER.md` |
| Measured sizes, row counts, QA, version findings, snapshot dates | `docs/DATA_SOURCES.md`, `data/README.md` |
| Method details implemented, and defaults approved by the Lead | `docs/SCIENTIFIC_METHODOLOGY.md` (approval first) |
| `harmonize_area()` module path; pipeline components | `docs/ARCHITECTURE.md` (approval first) |
| Validation results, including failures | `docs/VALIDATION_PLAN.md` |
| New risks or limitations | `docs/RISKS_AND_LIMITATIONS.md` |
| End of session | `docs/HANDOFF.md` and `docs/PROGRESS_LOG.md`, or a note in the PR asking the Lead to update them |

## 21. Branch, PR and escalation

**Branches:** use the name in the tracker, for example:
- `data/T-001-download-zips`
- `data/T-002-api-2026`
- `data/T-010-fixtures`
- `science/T-011-calibration`

Always create it from the latest `main`.

**PR flow:**
1. Commit the task prompt.
2. Open a draft PR titled `T-XXX: <title>`.
3. Implement, test and update docs.
4. Fill in `.github/pull_request_template.md`.
5. Mark it *Ready for review* and set your tracker row to `IN_REVIEW`.
6. Wait. If changes are requested, fix them in the **same PR**.

**The PR description must include:**
- task ID and link to the task prompt
- summary
- changed files
- commands run and their results (tests, row counts, timings)
- QA or validation tables where relevant
- documentation updated
- limitations and assumptions, each labelled verified / estimate / assumption / hypothesis
- **"needs Lead approval"** items (proposed defaults)
- scope issues
- confirmation of no secrets, no large files and no AI attribution

**Escalation:** if a task needs a change to the stack, architecture, contract, methodology or Member 3's code, or the data contradicts the documents:
1. Stop that part.
2. Describe it under "Scope issues" in the PR.
3. Set your tracker row to `BLOCKED` if you cannot continue.
4. Ask the Lead.

**Communicate integration needs early.** Tell Member 3 (through the Lead or a PR comment) as soon as fixtures, the stub or products are ready, or delayed.

## 22. Failure handling (summary)

| Situation | Action |
|---|---|
| Download or API failure | Retry with backoff; continue the rest; report the gaps; never substitute data |
| Unexpected schema or values | Record in QA; do not coerce silently; ask the Lead if it affects the method |
| Running behind at G1 | Tell the Lead; coarser grid or split years; Fallback A at G2 if the Lead triggers it |
| Calibration unstable or holdout poor | Report honestly at R2; the Lead decides on Fallback A |
| Combination not working by G3 | The Lead may trigger Fallback B |
| A validation test fails | Record it as `FAIL` with numbers; do not tune thresholds; propose what claim to narrow |
| A secret is committed by mistake | Tell the Lead immediately; rotate the key |

## S. Shared integration handoff (identical text in both teammate prompts)

> This section appears **word for word** in both `MEMBER_2_DATA_SCIENCE_PROMPT.md` and `MEMBER_3_APPLICATION_PROMPT.md`. If you find a difference between the two copies, stop and tell the Project Lead.
> **Source of truth:** `docs/DATA_CONTRACT.md` (`contract_version 0.1.0`, **APPROVED, decision D-016, 2026-11-14**). If this section and `DATA_CONTRACT.md` disagree, `DATA_CONTRACT.md` wins; report the discrepancy. Items marked **[PROPOSED ADDITION]** are not yet in `DATA_CONTRACT.md`. They become binding only when the Lead approves **D-022** and they are added to `DATA_CONTRACT.md` (version 0.1.1).

### S.1 Approval status (as of 2026-11-14 12:26 IST = H0; always re-check `docs/DECISION_LOG.md`)

| Decision | Topic | Status | Effect on work |
|---|---|---|---|
| D-003 | Product direction (Many Witnesses + Witness Stand) | Approved implicitly | Basis for everything |
| D-008 | Technology stack | **APPROVED 2026-11-14** (`TECH_STACK.md` §7) | Use exactly the approved stack |
| D-009 | Grid sizes | PROPOSED / OPEN, locked at Gate G1 | Member 2 computes candidates; the Lead locks them |
| D-010 | Baseline 2003–2022 | PROPOSED | Used by verdicts |
| D-015 | API owner | **APPROVED 2026-11-14: Member 3** | Member 3 builds the API |
| D-016 | Data contract v0.1.0 | **APPROVED 2026-11-14** (as written) | Fixtures and contract-dependent code may proceed |
| T-0D | Directory layout | **APPROVED 2026-11-14:** `pipeline/` (Member 2), `api/` and `app/` (Member 3) | Write code only in your own folders |
| D-022 | [PROPOSED ADDITION] items in this section | **PROPOSED** | Not binding until approved; build against them only if the Lead confirms |
| D-017 / D-020 | Team workflow / no AI attribution | Approved | Always apply |

### S.2 Directory layout and file names

```
data/
├── fixtures/v0.1.0/                 ← committed; SYNTHETIC only; total < 5 MB (produced by Member 2, T-010)
│   ├── README.md                    ← how the fixtures were generated; list of included edge cases
│   ├── cells.parquet
│   ├── cell_month_witness.parquet
│   ├── cell_month_harmonized.parquet
│   ├── entity_month.parquet
│   ├── calibration.parquet
│   ├── metadata.json                ← "synthetic": true
│   └── validation_results.json      ← "synthetic": true
├── raw/                             ← git-ignored (downloads)
├── interim/                         ← git-ignored (normalized detections)
└── products/                        ← REAL products, same file names as fixtures; committed via Git LFS (D-027)
```

- **Product path rule [PROPOSED ADDITION]:** each Parquet product is *either* a single file `<name>.parquet` *or* a directory `<name>/` of Parquet files, Hive-partitioned by `year=YYYY`. Consumers must accept both forms (read `<name>.parquet` if present, otherwise `<name>/**/*.parquet`).
- **Products location [PROPOSED ADDITION]:** the API reads from the environment variable `PRODUCTS_DIR`. Default: `data/fixtures/v0.1.0`. For real data: `data/products`. When the API is built, `PRODUCTS_DIR` is added to `.env.example`. It contains no secrets.

### S.3 Conventions

- **Coordinates:** WGS84, decimal degrees. Latitude in [−90, 90]; longitude in [−180, 180). A longitude of exactly 180 is treated as −180.
- **Cell bounds [PROPOSED ADDITION]:** the lower bound is inclusive, the upper bound exclusive, except the top row includes lat = 90.
- **`cell_id` format [PROPOSED ADDITION; final at G1 with D-009]:** `g{RRR}_r{row:04d}_c{col:04d}`.
  - `RRR` = the resolution in hundredths of a degree (`050` = 0.5°, `025` = 0.25°).
  - `row = floor((lat + 90) / res)`, counted from the south.
  - `col = floor((lon + 180) / res)`, counted from −180.
  - Example: `g050_r0123_c0456`.
- **Time:** all times are **UTC**. `year` and `month` are integers (1–12) for UTC calendar months. FIRMS `acq_time` is HHMM UTC. Strings in metadata use `YYYY-MM` for months and ISO-8601 for timestamps.
- **Record range:** the harmonized record starts at `2002-07`. `metadata.json` gives `latest_month` and `provisional_months`.
- **Missing data:** `null` means unknown or not applicable. **`0` is a real zero, never "unknown".** Never fill, interpolate or default missing values.
- **No detections vs below normal:** a place with no detections and a near-zero baseline is `NO_DETECTED_ACTIVITY`, **never** `BELOW_NORMAL`.
- **Uncertainty representation:**
  - `estimate` (Aqua-equivalent cell-days), `sd`, and the 90% interval `ci90_low` / `ci90_high`.
  - Probabilities `p_above`, `p_below`, `p_within` in [0, 1].
  - `disagreement_scale` ≥ 1 (null if fewer than 2 witnesses).
  - `estimate` is `null` only when no witness had usable data.
  - A `CANNOT_DETERMINE` verdict can still carry an estimate, usually with a wide interval.
- **Lists:** `witnesses_used` and `reason_codes` are `list<string>` in Parquet and arrays in JSON. `raw_by_witness` is a JSON-encoded string map `{witness: cell_days}`.
- **Enumerations** are exactly those in `DATA_CONTRACT.md`, uppercase:
  - `witness`: `AQUA_MODIS`, `TERRA_MODIS` (raw view only), `SNPP_VIIRS`, `NOAA20_VIIRS`, `NOAA21_VIIRS` (reserved)
  - `verdict`: `ABOVE_NORMAL`, `BELOW_NORMAL`, `WITHIN_NORMAL`, `CANNOT_DETERMINE`, `NO_DETECTED_ACTIVITY`
  - `reason_code`: `OUTAGE`, `INSUFFICIENT_BASELINE`, `INSUFFICIENT_OVERLAP`, `WITNESS_DISAGREEMENT`, `WIDE_INTERVAL`, `PROVISIONAL_NRT`, `AQUA_DRIFT_ERA`, `SINGLE_WITNESS`, `POOLED_CALIBRATION`, `DIURNAL_CAVEAT`
  - `data_level`: `SP`, `NRT`, `MIXED`
  - `entity_type`: `CELL`, `COUNTRY`, `CONTINENT`, `GLOBAL`, `CUSTOM`
- **Entity IDs [PROPOSED ADDITION]:**
  - `COUNTRY` → ISO 3166-1 alpha-3 (uppercase).
  - `CONTINENT` → `AF`, `AS`, `EU`, `NA`, `OC`, `SA` (`AN` only if it has data).
  - `GLOBAL` → `GLOBAL`.
  - `CUSTOM` → `custom_w{W}_s{S}_e{E}_n{N}`, with bounds rounded to 2 decimals.
  - `CELL` → its `cell_id`.

### S.4 SYNTHETIC fixtures (produced by Member 2 in T-010; consumed by Member 3)

- `metadata.json` and `validation_results.json` contain `"synthetic": true`. Every validation `test_id` starts with `SYNTHETIC-`, and its `notes` say "SYNTHETIC EXAMPLE — not a result".
- **Values are synthetic. Geography is real** (real ISO3 codes and real cell positions), so the map can be tested. The application must therefore show a persistent **"SYNTHETIC DATA — not NASA observations"** banner whenever `metadata.synthetic` is `true`.
- **Coverage:**
  - Grid `g050`, a few hundred cells spread over 4–6 countries on at least 3 continents.
  - Months `2002-07` through the latest month.
  - At least the `COUNTRY`, `CONTINENT` and `GLOBAL` entities in `entity_month`.
- **Realistic witness windows:**
  - `AQUA_MODIS` from 2002-07, excluded from `witnesses_used` after a placeholder drift cutoff, flagged `AQUA_DRIFT_ERA`.
  - `TERRA_MODIS` in raw rows only.
  - `SNPP_VIIRS` from 2012-01 to 2026-11 (partial final month).
  - `NOAA20_VIIRS` from 2018-04.
- **Required edge cases (all must be present and listed in the fixtures' `README.md`):**
  - every `verdict` value
  - every `reason_code` value
  - at least one outage month
  - the last two months marked provisional (`data_level = NRT`)
  - a cell with a zero baseline median (so `pct_of_normal = null`)
  - a record with `disagreement_scale > 1`
  - `NO_DETECTED_ACTIVITY` cells
  - a `null` estimate
- Fixtures must validate against `DATA_CONTRACT.md` (fields, types, enums, null rules). The generator script is committed with them so they can be regenerated.

### S.5 API expectations (endpoints from `docs/ARCHITECTURE.md` §5)

**Response envelope [PROPOSED ADDITION]:** every JSON response is
`{"contract_version": "0.1.0", "method_version": "<string>", "synthetic": <bool>, "data": <payload>}`

**Errors [PROPOSED ADDITION]:**
- Body: `{"error": {"code": "<UPPER_SNAKE>", "message": "<human text>"}}`
- Status codes:
  - `400` invalid parameters
  - `404` unknown entity
  - `422` invalid or oversize custom area (the implementation may cap the size, but must say so in the message)
  - `503` products unavailable

| Endpoint | `data` payload |
|---|---|
| `GET /api/meta` | The `metadata.json` object |
| `GET /api/entities?type=COUNTRY\|CONTINENT` | `[{entity_type, entity_id, entity_name, bbox: [W,S,E,N]}]` |
| `GET /api/map?year=&month=&layer=verdict\|raw\|harmonized` | One record per analysis cell: `cell_id, lat_min, lat_max, lon_min, lon_max` plus that cell-month's `cell_month_harmonized` fields |
| `GET /api/series?entity_type=&entity_id=` | `entity_month` records for the entity, ordered by `year`, `month` |
| `POST /api/series/custom` with body `{"bbox": [W,S,E,N]}` | `entity_month`-shaped records with `entity_type = "CUSTOM"`, computed by `harmonize_area()` over the cells whose **centres** fall inside the box |
| `GET /api/evidence?entity_type=&entity_id=&year=&month=` | One `entity_month` record, with `raw_by_witness` decoded into an object |
| `GET /api/anomalies?year=&month=&limit=` | `[{entity_type, entity_id, entity_name, verdict, p_above, p_below, pct_of_normal}]`. Only `ABOVE_NORMAL` / `BELOW_NORMAL`, sorted by `max(p_above, p_below)` descending |
| `GET /api/validation` | The `validation_results.json` object |
| `GET /api/export.csv?entity_type=&entity_id=` (or `bbox=`) | CSV of the `entity_month` fields, with `raw_by_witness` expanded into `raw_<witness>` columns. It starts with `#` comment lines giving `method_version`, `contract_version`, data snapshot date, `synthetic` flag and citation |

**Science boundary:**
- The API and the frontend **never** compute science: no conversions, baselines, probabilities or verdicts.
- Custom areas call `harmonize_area(cell_ids, months=None) -> list[EntityMonthRecord]` (`DATA_CONTRACT.md` §8), which Member 2 provides.
- It lives under `pipeline/` (T-0D). Member 2 documents its exact module path in `docs/ARCHITECTURE.md` when it is created.

### S.6 Hand-off timeline (H = hours after the Lead approves D-008 and D-016)

| When | From → To | What |
|---|---|---|
| H3 | M2 → M3 | SYNTHETIC fixtures + fixtures `README.md` (T-010) |
| H10 | M2 → M3 | `harmonize_area()` **stub** with the final signature, returning fixture-derived records |
| H22 | M2 → M3 | Real products in `data/products/` (committed via Git LFS, D-027) + real `harmonize_area()` |
| H26 | M2 → M3 | Real `validation_results.json` with actual statuses |
| Any time | M3 → Lead → M2 | Integration needs or contract gaps, raised as a PR comment or tracker note to the Lead. **Never** by editing the other workstream's code |

### S.7 Change control

A contract change needs:
1. A proposal to the Lead.
2. Lead approval, logged in `DECISION_LOG.md`.
3. `DATA_CONTRACT.md` updated, with `contract_version` bumped.
4. Fixtures regenerated under the new version folder.
5. Both members notified.

Then the code changes. Nobody changes field names, types, enums or semantics on their own.
