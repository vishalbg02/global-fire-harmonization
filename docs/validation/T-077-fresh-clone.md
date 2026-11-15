# T-077: fresh-clone reproducibility check

> Member 2 · 2026-11-15 · Windows 11, Git Bash, Python 3.13.7, Node 22.18.0, Git LFS. A clean clone of `https://github.com/vishalbg02/global-fire-harmonization.git` in an empty folder, then only the README steps. Times are wall-clock on one machine and vary.

## 1. Steps and results

| # | Step (command) | Result | Time |
|---|---|---|---|
| 1 | `git clone` (branch of the README, T-075 at the time), `git lfs install`, `git lfs pull` | OK. Five Parquet files and two JSON files in `data/products/`; the LFS object ids equal the SHA-256 values recorded in PR #52 (for example `cell_month_harmonized.parquet` starts `ce9304ce`) | 3 min 36 s |
| 2 | `python -m venv .venv`; `.venv/Scripts/pip install -r api/requirements.txt` | OK | 2 min 36 s |
| 3 | `pytest pipeline/tests api/tests` on the README branch | **1 failure**: `api/tests/test_static_export.py::test_every_file_is_the_apis_own_answer` (and the same test failed in my normal checkout). Cause: the test read the exported UTF-8 JSON with `Path.read_text()` and no encoding; on Windows that is cp1252, so the em dash of the SYNTHETIC fixture text came back different. Not a code or data defect. **Fixed** in the test files (`read_text("utf-8")`, here and in `test_static_sample.py`) | 4 min 47 s |
| 4 | `ruff check pipeline api` on the README branch | **3 errors** (the ones the Lead listed: `download_zips.py` BLE001 and FURB122, `check_modis_availability.py` FURB192). **Fixed**, behaviour unchanged (`max()` of the paths, `writelines`, and a suppression with its reason on the deliberate catch-all that records a failed download and continues) | 1 s |
| 5 | `cd app && npm ci` | OK, 122 packages | 19 s |
| 6 | `npm test`, `npm run typecheck`, `npm run lint`, `npm run build` | OK: 23 files, 451 tests pass; typecheck, lint and build clean | 9 s, 2 s, 1 s, 3.5 s |
| 7 | API as the README first said (`cd api` then `uvicorn fire_api.main:app`) | **Failed**: every endpoint answered 503 "Product file not found". The default products folder `data/products` is relative to the folder the server is started from (`api/fire_api/products.py`), so it is not found from `api/`. **Fixed in the README:** start from the repository root with `--app-dir api` | n/a |
| 8 | API from the repository root: `.venv/Scripts/uvicorn fire_api.main:app --app-dir api --port 8000` (the corrected step; equal to the working `PRODUCTS_DIR=../data/products` run) | OK: `/api/meta` 200 (`synthetic` false, method 0.1.0, latest month 2026-11); `/api/validation` 200 (PASS 18, FAIL 18, INCONCLUSIVE 2); `/api/series` for Indonesia 200, 293 months, 2015-09 ABOVE_NORMAL at 265% | under 0.2 s per request |
| 9 | `npm run dev` | OK: the page and the `/api` proxy answer 200; the methods page shows "FAIL: 18, INCONCLUSIVE: 2, PASS: 18, NOT RUN: 0"; the Indonesia 2015-09 view loads with a verdict and no console error | starts in under 1 s |

Steps 8 and 9 were run with the README branch's app; the PowerShell variants of the commands (`.venv\Scripts\...`) were not run (Git Bash was used).

## 2. After the corrections (branch `chore/T-077-fresh-clone`)

Re-run in the same clean clone on the T-077 branch (the README fix and the test fixes in place):

| Step | Result |
|---|---|
| `ruff check pipeline api` | All checks passed |
| `pytest pipeline/tests api/tests` | **751 passed, 17 skipped** (7 min 52 s); the one failure of step 3 is gone |
| `python pipeline/contract_check.py data/products --real` (all tables) | **Not completed: memory error** (`ArrowMemoryError: malloc of size 3518699200 failed`, then `numpy ArrayMemoryError` 1.09 GiB) on a 15.6 GB machine with 7.2 GB free, twice. The checker loads each whole table into pandas (the 420 MB table has 16.5 million rows). **Not fixed here** (a change to the checker is outside this task); the README now says so |
| Contract check on the small tables (`check_dir(..., real=True, only=('entity_month', 'cells', 'calibration'))`) | **0 errors** (2.6 s). The full-table check last ran with 0 errors on 2026-11-14 (PR #52, on a machine with more free memory); it was **not re-verified** in this clean clone |

## 3. What this does and does not show

- **Verified:** the README steps above work from a clean clone on this machine (Windows, Git Bash) after the corrections, **except the full-table contract check, which needs more free memory than this machine had** (see section 2); the products downloaded through LFS are the committed ones.
- **Not verified:** macOS or Linux, PowerShell variants, a machine without Git LFS configured beforehand (the README says to run `git lfs install`), the offline copy, and Node 24.
- The test count of the app (451) and the Lead's count of 744 Python tests are as run on the dates above; they are not fixed numbers.
