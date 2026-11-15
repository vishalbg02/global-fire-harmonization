# Task prompt: T-086 Jammu and Kashmir cells by India's official boundary (D-033)

> Prepared for: Member 2 · Date: 2026-11-15 · Based on main (HEAD at branch creation)
> Source of truth: the Lead's comment on PR #74 (T-086 / D-033, 2026-11-15): "reassign those cells' country with Natural Earth's India point-of-view file, regenerate `cells.parquet` and the IND, PAK and CHN rows of `entity_month` (LFS), then re-run the contract, number and featured-story checks." The Lead set this task **after the presentation**; this PR is for the Lead to merge then.

## 1. Project context
FIRMS file names give the country of each detection, and a cell takes the country with most detections (`pipeline/gridding.py`, `build_cells`). In Jammu and Kashmir this follows FIRMS's attribution: in the box 72.5 to 80.5 degrees E and 32.5 to 37.2 degrees N, 42 cells are Pakistan, 27 China, 39 India and 1 none (measured on `cells.parquet`, risk S23). The Lead decided to follow India's official boundary for the project.

## 2. Task objective
Reassign the country of the cells in the Jammu and Kashmir box that fall inside India under Natural Earth's India point-of-view boundary, with a reproducible script, and regenerate the affected products: `cells.parquet` and the IND, PAK and CHN rows of `entity_month`.

## 3. Assigned responsibility
T-086 / after the presentation · Owner: Member 2 · Reviewer and merger: Member 1 (the Lead merges; this PR changes Git LFS products).

## 4. Relevant files and directories
- Read: `pipeline/gridding.py`, `pipeline/country_mapping.py`, `pipeline/verdicts.py` (`entity_month`), `docs/DATA_SOURCES.md` section 6, `docs/RISKS_AND_LIMITATIONS.md` (S23)
- Create: `pipeline/kashmir_cells.py` (the reassignment and the regeneration of the three entities), `pipeline/tests/test_kashmir_cells.py`, `docs/validation/T-086-kashmir-cells.md` (counts, checks)
- Modify: `data/products/cells.parquet` and `data/products/entity_month.parquet` (Git LFS), `docs/DATA_SOURCES.md` (new subsection), `docs/RISKS_AND_LIMITATIONS.md` and `docs/DECISION_LOG.md` only as the instructions in section 13 say
- Not touched: method, thresholds, verdict code, `cell_month_harmonized.parquet`, `cell_month_witness.parquet`, `calibration.parquet`, `metadata.json`, `validation_results.json`, `api/`, `app/`

## 5. Approved technologies
Python, NumPy, pandas, PyArrow, DuckDB, pytest, ruff (D-008). **No new dependency:** the point-in-polygon test is written with NumPy (no shapely).

## 6. Architecture and data contract
No contract change. `cells.parquet` keeps every column, row, cell id and order; only `country_iso3` of the reassigned cells changes.

## 7. Inputs
- **Natural Earth India point-of-view boundary:** `ne_10m_admin_0_countries_ind.geojson`, version 5.1.1, 13,242,091 bytes, from `https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/geojson/ne_10m_admin_0_countries_ind.geojson`, saved in an empty folder `C:/IgnisLine-data/ne_ind/` (outside the repository); SHA-256 recorded in DATA_SOURCES. Approved by the user on 2026-11-15.
- The final products on `main` (T-014).

## 8. Expected outputs
The reassignment list (cell ids, old and new country), the regenerated products with SHA-256 values, the check results, and the documentation.

## 9. Implementation requirements
1. **Resolution mix, labelled limitation:** Natural Earth publishes the point-of-view country files at **1:10m only**; the existing country mapping uses the **1:50m** default (T-009, version 5.1.1). The 1:10m boundary is more detailed. To keep the change local: only cells in the Jammu and Kashmir box (72.5 to 80.5 E, 32.5 to 37.2 N) are considered; every other differing cell outside the box is **reported, not changed**.
2. **Rule:** a cell in the box is reassigned to India if its **centre** lies inside the India polygon of the India point-of-view file and its current country is not India. A cell whose current country is India but whose centre is outside the India polygon is **reported, not changed**. The cell centre is the rule the API uses for custom areas. Point-in-polygon uses the even-odd rule over every ring (holes included).
3. **Reproducible:** one script, one command, no hand edits; the list of changed cells is written to `data/interim/qa/` and summarised in the report.
4. **cells.parquet:** only `country_iso3` of the reassigned cells changes (`continent` stays Asia: verified). `stratum_id`, `fire_region` and every other column are unchanged (the stratum is a 2.5 degree block inside a fire region, not a country: verified), so the calibration is unaffected.
5. **entity_month:** compute `entity_month` with the **same code** (`verdicts.entity_month`) on the new `cells.parquet`; replace the rows of the COUNTRY entities IND, PAK and CHN for every month; keep every other row; **verify** that every other row (all other countries, the continents, the world) is equal in value to the one on `main` (exact for strings and integers, bit-equal for floats). Entity names, `n_cells` and `raw_by_witness` follow the new membership.
6. **Not regenerated, stated:** `cell_month_harmonized.parquet` keeps its values. One consequence is recorded as a labelled limitation: the cell-level caveat `DIURNAL_CAVEAT` (D-028: India, October and November from 2020) is set from the cell's country when the cell table is built, so the reassigned cells do not carry it in the cell table until that table is regenerated; verdicts and values are unaffected by it (a caveat never changes a verdict). The entity rows follow the new country.
7. **Checks to re-run:** `contract_check` (small tables; the full check if memory allows), `number_check.py`, `featured_stories.py --check`, `analytics_check.py` if it reads these entities, the pytest files of the touched modules, `ruff`.
8. Products only through Git LFS; SHA-256 values are reported in the PR (`data/README.md`).

## 10. Constraints: do not modify
Method, thresholds, verdict code, the validation results, the other products, `api/`, `app/`, no secrets, no data files except the two products.

## 11. Acceptance criteria
The India point-of-view cells are India in `cells.parquet`; IND, PAK and CHN rows are regenerated and the rest of `entity_month` is value-equal to `main`; every check passes or its failure is reported; the 1:10m versus 1:50m limitation is stated in this prompt, DATA_SOURCES and the PR.

## 12. Required tests
`python -m pytest pipeline/tests/test_kashmir_cells.py -q` on SYNTHETIC polygons and cells with known answers (point in polygon with holes and multipolygons, boundary points, the reassignment rule and what is only reported, the merge of entity rows keeps the other rows). `ruff` clean.

## 13. Documentation updates
`docs/DATA_SOURCES.md` (new subsection: file, version, size, SHA-256, counts, labels, the resolution limitation); `docs/RISKS_AND_LIMITATIONS.md` S23 is added by PR #86: if it is on `main` when this PR is final, S23 is updated to the resolved state (with the remaining DIURNAL_CAVEAT note); otherwise the PR states it; `docs/DECISION_LOG.md` D-033: a status note if the entry exists on `main`.

## 14. Git branch and PR instructions
Branch `science/T-086-kashmir-cells` from the latest `main`; first commit: this prompt; open a PR with the template, stating that it changes LFS products and is for the Lead to merge after the presentation; never merge; human identity; no AI attribution (D-020).

## 15. Out-of-scope or blocking issues
- The map drawing (T-085) is Member 3's.
- Regenerating `cell_month_harmonized.parquet` for the caveat above is a separate decision for the Lead.
