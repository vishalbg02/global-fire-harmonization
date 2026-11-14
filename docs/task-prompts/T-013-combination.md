# Task prompt: T-013 Witness combination with disagreement inflation, and `harmonize_area()`

> Prepared for: Member 2 · Date: 2026-11-14 · Based on main @ aa79228
> Source of truth: docs/TASK_TRACKER.md row T-013 (assigned by the Lead's assignment PR #27; T-011 is merged). This prompt adds no scope beyond it.

## 1. Project context
NASA Space Apps Challenge 2026 team project (Many Witnesses + Witness Stand): harmonize NASA FIRMS hotspot detections from several satellites (`docs/PROJECT_PLAN.md`). T-006 produced per-witness cell-month observations and T-011 the calibration ratios that convert each VIIRS witness to the Aqua-equivalent scale. T-013 combines the converted witnesses into one estimate with an honest uncertainty, for any area. The baseline, probabilities and verdicts (T-014) and the holdout evaluation and Aqua drift diagnostic (T-012) come later. Member 3's API calls `harmonize_area()` for custom areas (`api/fire_api/custom.py`).

## 2. Task objective
A module `pipeline/harmonize.py` with the single implementation of the science for an area: per witness and month a converted estimate with variance, a precision-weighted combined estimate, disagreement inflation, and `harmonize_area(cell_ids, months=None)` returning contract-shaped `entity_month` records (`docs/DATA_CONTRACT.md` §4, §8). The combination design is reported as a proposal for the Lead's approval.

## 3. Assigned responsibility
- Task ID / priority: T-013 / P0
- Owner: Member 2 (Data Engineering & Scientific Analysis)
- Reviewer and merger: Member 1 (Project Lead)
- Dependencies (must be MERGED first): T-011 (merged, #36)

## 4. Relevant files and directories
- Read: the assistant instructions file at the repository root, `docs/SCIENTIFIC_METHODOLOGY.md` §4.3 to §4.5, `docs/DATA_CONTRACT.md` §2, §4, §5 and §8, `docs/prompts/MEMBER_2_DATA_SCIENCE_PROMPT.md` §13 and §18, `docs/DATA_SOURCES.md` (T-006, T-011), `pipeline/calibration.py`, `api/fire_api/custom.py` (the caller, read only)
- Create/modify:
  - `docs/task-prompts/T-013-combination.md` (this file)
  - `pipeline/harmonize.py`
  - `pipeline/tests/test_harmonize.py`
  - `docs/DATA_SOURCES.md` (the combination design, assumptions and the real-data checks)
  - `docs/TASK_TRACKER.md` (row T-013 only)
- Not committed: everything under `data/products/`

## 5. Approved technologies
Python, NumPy, pandas, DuckDB, pyarrow, pytest, ruff (D-008). No new dependency.

## 6. Architecture and data contract
Input: `cell_month_witness` (§2), `cells` (§1, with the final `stratum_id`) and `calibration` (§5). Output: records in the shape of §4 (`entity_month`; `entity_type = "CUSTOM"` for `harmonize_area()`). No contract change. The baseline, probabilities and verdicts are T-014's: here the baseline fields are `null` and the verdict is `CANNOT_DETERMINE`, as the contract requires without a baseline.

## 7. Inputs
`data/products/cell_month_witness.parquet`, `cells.parquet` and `calibration.parquet` (final T-011 products, D-025 mask).

## 8. Expected outputs
`pipeline/harmonize.py` and its tests. A report on real data: a small set of areas and months (for example Indonesia 2015 and a savanna control) showing the per-witness estimates, the combined estimate, the interval, `disagreement_scale` and the reason codes, and the distribution of `disagreement_scale` over a sample of country-months.

## 9. Implementation requirements
1. **Per witness and month** (witnesses `AQUA_MODIS`, `SNPP_VIIRS`, `NOAA20_VIIRS`; Terra is raw view only): `E_w = sum over strata and day/night of ratio x cell_days`, with the ratio of the stratum, witness, day/night (`D`, `N` separately; `ALL` is not used) and season of the month. Aqua has ratio 1 and no uncertainty.
2. **Variance:** `ratio^2 x var(cell_days) + cell_days^2 x ratio_sd^2` per stratum and day/night, with `var(cell_days) = cell_days` (a Poisson approximation; overdispersion makes it optimistic, which test D1 measures). **State the assumption.** A floor stops a zero count from having zero variance (proposal in the report).
3. **Stratum first:** sum the raw `cell_days` of the area per witness, stratum and day/night, convert per stratum, then add. Never sum per-cell intervals; strata are treated as independent (limitation: errors shared through the pooling parents are not propagated).
4. **Combined estimate:** the precision-weighted mean of the available `E_w`. `S = sqrt(chi^2 / (N - 1))` multiplies the combined sd only when `S > 1`; `disagreement_scale` is that factor (null with fewer than 2 witnesses, otherwise at least 1; reason `WITNESS_DISAGREEMENT` when `S > 1`). With one witness: reason `SINGLE_WITNESS`.
5. **Which witnesses count in a month:** only a witness with every day of the month available (`days_available = days_in_month`), as in T-011; a partial month would undercount. An optional `aqua_cutoff` (year, month) removes Aqua from the combination after it (reason `AQUA_DRIFT_ERA`); its value comes from T-012 and **defaults to none**. No cutoff is chosen here.
6. **Raw fields:** `raw_combined_cell_days`, `raw_by_witness` (all operating witnesses, Terra included) and `n_cells`, as in the contract. `data_level` is `SP` or `NRT` when all witness rows agree, otherwise `MIXED`; reason `PROVISIONAL_NRT` for `NRT` or `MIXED`.
7. **Interval:** a 90% normal interval `estimate +/- 1.645 sd`, lower bound at 0.
8. **`harmonize_area(cell_ids, months=None)`:** the one function used by the batch and by the API; deterministic; records ordered by year and month; plain dicts in contract shape.
9. **No estimate without a witness:** if no witness counts in a month, `estimate`, the interval and `sd` are `null`, `n_witnesses` is 0, and the verdict is `CANNOT_DETERMINE`.

## 10. Constraints: do not modify
- Do not change the tech stack, architecture, scientific methodology or data contract. Do not add an enumeration value.
- Do not edit files outside §4 "Create/modify". Do not touch `api/` or `app/`.
- No secrets, no data files, no direct pushes to `main`, no self-merge.
- Do not compute baselines, probabilities or verdicts (T-014), the holdout evaluation or drift diagnostic (T-012) or any validation test. Do not fix the Aqua drift cutoff. Do not present proposals as approved.

## 11. Acceptance criteria
Unit tests on synthetic data with known answers pass (the tracker's criterion), and `harmonize_area()` returns contract-shaped records on the real products.

## 12. Required tests
`python -m pytest pipeline/tests/test_harmonize.py -q` on synthetic data with known answers: equal witnesses give `S <= 1` and no inflation; conflicting witnesses give `S > 1` and a widened sd; a single witness gives `SINGLE_WITNESS` and a null scale; the estimate of an area with two strata of different ratios equals the stratum-first sum (and differs from one pooled ratio); the precision-weighted mean is right; a partial-month witness is excluded; `aqua_cutoff` removes Aqua with `AQUA_DRIFT_ERA`; a month without a usable witness gives a null estimate; the output is deterministic, ordered, and contract-shaped (checked with `contract_check` on the records); `months` filters. `ruff` passes on the files of this task. Then the run on the real products, with the report.

## 13. Documentation updates
`docs/TASK_TRACKER.md` row T-013; `docs/DATA_SOURCES.md`.

## 14. Git branch and PR instructions
- Branch: `science/T-013-combination` created from the latest `main`
- First commit: this prompt file
- Open a DRAFT PR early; fill in `.github/pull_request_template.md`
- Never merge; wait for the Project Lead
- Commit with your own Git identity (D-020)

## 15. Out-of-scope or blocking issues
- **Needs the Lead's approval (proposals):** day and night converted separately and added; the zero-count variance floor; only complete witness-months count; strata treated as independent; the reason code rule for `WITNESS_DISAGREEMENT` (any `S > 1`); the interval form.
- **Aqua drift cutoff:** `aqua_cutoff` stays unset until T-012 measures it (D-005).
- **Raw-only products (#40):** independent of this task; `harmonize_area()` does not read them.
