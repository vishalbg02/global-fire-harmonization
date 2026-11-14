# Task prompt: T-004 Fire-region mask (GFED basis regions)

> Prepared for: Member 2 · Date: 2026-11-14 · Based on main @ c8071b1
> Source of truth: docs/TASK_TRACKER.md row T-004 (owner changed from M1 to M2 by the Lead's assignment PR #27). This prompt adds no scope beyond it.

## 1. Project context
NASA Space Apps Challenge 2026 team project (Many Witnesses + Witness Stand): harmonize NASA FIRMS hotspot detections from several satellites (`docs/PROJECT_PLAN.md`). Calibration ratios between satellites differ by fire regime, so they are shrunk toward a fire-region ratio and then toward a global ratio (partial pooling, `SCIENTIFIC_METHODOLOGY.md` §4.3). The fire region is the pooling parent. The contract field is `cells.fire_region` ("GFED basis region code or fallback").

## 2. Task objective
A reusable lookup that gives every analysis cell a `fire_region`: the 14 GFED basis regions (BONA, TENA, CEAM, NHSA, SHSA, EURO, MIDE, NHAF, SHAF, BOAS, CEAS, SEAS, EQAS, AUST) taken from the GFED4s basis-regions grid, with explicit, counted rules for cells where the grid has no land. A measured report shows how many cells and detections fall under each rule.

## 3. Assigned responsibility
- Task ID / priority: T-004 / P0
- Owner: Member 2 (Data Engineering & Scientific Analysis)
- Reviewer and merger: Member 1 (Project Lead)
- Dependencies (must be MERGED first): none (T-005 and T-009 are merged and used for the coverage report)

## 4. Relevant files and directories
- Read: the assistant instructions file at the repository root, `docs/DATA_SOURCES.md` §6, `docs/DATA_CONTRACT.md` (`cells`), `docs/SCIENTIFIC_METHODOLOGY.md` §4.3, `docs/prompts/MEMBER_2_DATA_SCIENCE_PROMPT.md` §S.3
- Create/modify:
  - `docs/task-prompts/T-004-region-mask.md` (this file)
  - `pipeline/fire_regions.py` (build, lookup and coverage report)
  - `pipeline/tests/test_fire_regions.py`
  - `docs/DATA_SOURCES.md` (§6: source, licence note, rules, measured coverage)
  - `docs/TASK_TRACKER.md` (row T-004 only)
- Not committed: the downloaded HDF5 file and the derived grids under `data/interim/fire_regions/`

## 5. Approved technologies
Python, NumPy, pyarrow, DuckDB (D-008). **h5py is not in the approved stack**: it is used only once, to read the GFED HDF5 file and write a plain NumPy array; the lookup itself needs only NumPy. Raised for the Lead.

## 6. Architecture and data contract
No contract product is changed. `fire_region` is a string, one of the 14 GFED codes or a fallback code. The analysis cell format follows the proposed `cell_id` convention `g{RRR}_r{row:04d}_c{col:04d}` (D-022).

## 7. Inputs
- `GFED4.1s_2001.hdf5` (30,765,559 bytes, SHA-256 `1b684bf0b348e92a5d63ea660564f01439f69c4eb88eacd46280237d51ce5815`) from http://www.geo.vu.nl/~gwerf/GFED/GFED4/ (public, no login), downloaded locally with Member 2's approval. Only its `ancill/basis_regions` array (720 x 1440, 0.25 degrees, classes 0 = ocean, 1 to 14 = regions) is read.
- The normalized detections (T-003) for the coverage report.

## 8. Expected outputs
- `data/interim/fire_regions/basis_regions_0.25.npy` and `fire_region_g050.parquet` (one row per 0.5 degree cell: `cell_id`, `fire_region`, `method`), local only.
- A coverage report in `docs/DATA_SOURCES.md`: cells per region and method, ties, detections per region and method.

## 9. Implementation requirements
1. Cell value: the most common GFED region among the land 0.25 degree sub-cells of the analysis cell. A tie takes the lowest region number (documented, counted).
2. A cell with no land sub-cells takes the region of the nearest land cell within 1.0 degree (method `NEAREST_LAND`); otherwise the code `UNASSIGNED` (method `UNASSIGNED`, pooled directly to the global ratio). These rules are proposals for the Lead.
3. Every analysis cell gets a value; nothing is left null.
4. The lookup works for any analysis grid size (cell bounds in, region out), because D-009 is not locked.
5. Measure on the real detections how many detections fall in each region and under each method. Report, never hide, the share that is not plain GFED.

## 10. Constraints: do not modify
- Do not change the tech stack, architecture, scientific methodology or data contract.
- Do not edit files outside §4 "Create/modify". Do not touch `api/` or `app/`.
- No secrets, no data files, no direct pushes to `main`, no self-merge.
- Do not commit the GFED file or grids. Cite GFED (van der Werf et al., 2017) where the source is described.

## 11. Acceptance criteria
Every analysis cell has a `fire_region`.

## 12. Required tests
`python -m pytest pipeline/tests/test_fire_regions.py -q` on a small synthetic grid with known answers (lookup at edges and across the date line, cell mode, tie rule, nearest-land fill within and beyond the radius, `UNASSIGNED`, every cell assigned, cell_id format), plus checks on the real grid when it is present locally (14 regions found; spot checks such as Borneo EQAS, Sahara NHAF, Amazon SHSA, Europe EURO). `ruff` passes on the files of this task.

## 13. Documentation updates
`docs/TASK_TRACKER.md` row T-004; `docs/DATA_SOURCES.md` §6.

## 14. Git branch and PR instructions
- Branch: `science/T-004-region-mask` created from the latest `main`
- First commit: this prompt file
- Open a DRAFT PR early; title "T-004: Fire-region mask (GFED basis regions)"; fill in `.github/pull_request_template.md`
- Never merge; wait for the Project Lead
- Commit with your own Git identity (D-020)

## 15. Out-of-scope or blocking issues
- The tracker shows T-004 as `TODO` until the Lead's assignment PR #27 is merged; work started on Member 2's go-ahead. The Lead should confirm.
- Needs Lead approval: GFED4s (not GFED5) as the source of the region grid; the fallback rules and the code `UNASSIGNED`; h5py used for the one-time read.
- GFED data are free to use with citation; the licence terms were not independently verified beyond the project pages **[ASSUMPTION]**.
