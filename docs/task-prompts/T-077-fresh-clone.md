# Task prompt: T-077 Fresh-clone reproducibility check and the ruff errors

> Prepared for: Member 2 · Date: 2026-11-15 · Based on main (HEAD at branch creation)
> Source of truth: `docs/TASK_TRACKER.md` row T-077 (PR #74) and the Lead's audit of 2026-11-15 (3 ruff errors in `pipeline/`).

## 1. Project context
A judge or a new teammate will clone the repository and follow the README. The README (T-075) was written before it had been run from a clean clone.

## 2. Task objective
Follow the README on a clean clone, record every step and its result, correct every step that does not work, and make `ruff check pipeline` pass.

## 3. Assigned responsibility
T-077 / P0 · Owner: Member 2 · Reviewer and merger: Member 1 · Dependency: T-075 (merged).

## 4. Relevant files and directories
- Modify: `README.md` (only steps that fail as written), `pipeline/download_zips.py`, `pipeline/check_modis_availability.py` (ruff), and a test file only if a test fails on a clean clone for a reason that is not the code (for example a platform default)
- Create: `docs/validation/T-077-fresh-clone.md` (every step, command, result, time)
- Do not touch: method, products, thresholds, app code

## 5. Approved technologies
None added.

## 6. Architecture and data contract
No change.

## 7. Inputs
A fresh clone of the repository from GitHub (Git LFS products included), Python 3.13, Node 22.

## 8. Expected outputs
The report, the corrected README steps, `ruff check pipeline api` clean.

## 9. Implementation requirements
1. Clone from GitHub into an empty folder, `git lfs pull`, create the virtual environment and install `api/requirements.txt` exactly as the README says; run the tests, ruff, the contract check, `npm ci`, the app tests, typecheck, lint and build; start the API and the app as the README says and check the pages.
2. Record each step with the exact command, the result and the time; a failure is recorded with the exact error and what was changed.
3. Fix the ruff errors without changing behaviour (`pipeline/download_zips.py` two, `pipeline/check_modis_availability.py` one). A suppression is allowed only with its reason.
4. No claim that a step works unless it ran in the clean clone.

## 10. Constraints: do not modify
Method, thresholds, products, validation results, `docs/HANDOFF.md`, `docs/PROGRESS_LOG.md`.

## 11. Acceptance criteria
Every step and its result recorded; `ruff check pipeline api` clean; a newcomer can run the app from the README.

## 12. Required tests
The full suites in the clean clone: `pytest pipeline/tests api/tests`, `npm test`, typecheck, lint, build, contract check.

## 13. Documentation updates
`docs/validation/T-077-fresh-clone.md`; README steps that failed.

## 14. Git branch and PR instructions
Branch `chore/T-077-fresh-clone` from the latest `main`; first commit: this prompt; open a PR with the template; never merge; human identity (D-020).

## 15. Out-of-scope or blocking issues
Screenshots and the UI are Member 3's.
