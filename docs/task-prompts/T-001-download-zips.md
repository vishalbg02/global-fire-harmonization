# Task prompt: T-001 Download all global zips

> Prepared for: Member 2 · Date: 2026-11-14 · Based on main @ 14a5e35
> Source of truth: docs/TASK_TRACKER.md row T-001. This prompt adds no scope beyond it.

## 1. Project context
NASA Space Apps Challenge 2026 team project (Many Witnesses + Witness Stand): harmonize NASA FIRMS hotspot detections from several satellites so fire activity can be compared across 2002–2026 (`docs/PROJECT_PLAN.md`). T-001 is the first step of the pipeline: acquiring the historical global yearly archives. Everything downstream (T-003 normalize, T-005 QA, T-006 gridding) reads what this task downloads.

## 2. Task objective
All 46 FIRMS global zips (MODIS 2002–2025, S-NPP 2012–2025, NOAA-20 2018–2025) are present in `data/raw/zips/`, each verified against the HTTP `Content-Length` and `unzip -t`, with SHA-256 checksums in a manifest kept outside Git. The snapshot is recorded in `data/README.md`, and measured sizes are compared with `docs/DATA_SOURCES.md`.

## 3. Assigned responsibility
- Task ID / priority: T-001 / P0
- Owner: Member 2 (Data Engineering & Scientific Analysis)
- Reviewer and merger: Member 1 (Project Lead)
- Dependencies (must be MERGED first): none (stack-independent)

## 4. Relevant files and directories
- Read: the assistant instructions file at the repository root, `docs/DATA_SOURCES.md`, `data/README.md`, `docs/prompts/MEMBER_2_DATA_SCIENCE_PROMPT.md` §5–6, `docs/TASK_TRACKER.md`
- Create/modify:
  - `docs/task-prompts/T-001-download-zips.md` (this file)
  - `pipeline/download_zips.py` (standard-library Python only)
  - `data/README.md` (Snapshot record table only)
  - `docs/TASK_TRACKER.md` (row T-001 only)
  - `docs/DATA_SOURCES.md` (measured sizes, only where they replace estimates)
- Not committed: everything under `data/raw/`

## 5. Approved technologies
Python (approved, D-008) and `curl`/`unzip` are not required; the script uses the Python standard library only. No new dependency.

## 6. Architecture and data contract
Not touched. This task produces no contract product. It writes only to `data/raw/zips/`.

## 7. Inputs
`https://firms.modaps.eosdis.nasa.gov/data/country/zips/{SENSOR}_{YYYY}_all_countries.zip` for `modis` 2002–2025, `viirs-snpp` 2012–2025, `viirs-jpss1` 2018–2025. No login, no key.

## 8. Expected outputs
- 46 zip files in `data/raw/zips/`.
- A manifest `data/raw/zips/MANIFEST.tsv` (name, bytes, expected bytes, sha256, integrity result), git-ignored.
- Filled "Global zips" row in `data/README.md`.
- File count, total bytes and dates in the PR description.

## 9. Implementation requirements
1. Resumable download, retry with backoff.
2. Order: MODIS, then S-NPP, then NOAA-20.
3. Compare each file's size with `Content-Length`; test integrity with the zip central directory and CRC test.
4. A zip that fails repeatedly is recorded and skipped; report the missing years. Never substitute other data.
5. Re-running is idempotent: complete, verified files are skipped.
6. Check free disk space before starting.

## 10. Constraints: do not modify
- Do not change the tech stack, architecture, scientific methodology or data contract.
- Do not edit files outside §4 "Create/modify". Do not touch `api/` or `app/`.
- No secrets, no data files, no direct pushes to `main`, no self-merge.
- Do not unzip or normalize (that is T-003). Do not mark measurements as verified unless they were measured.

## 11. Acceptance criteria
All files present; sizes match `DATA_SOURCES.md` (within what the server reports); snapshot recorded in `data/README.md`.

## 12. Required tests
- Re-run the script: it must report 46/46 verified and download nothing.
- `unzip -t` / CRC test passes on every file.

## 13. Documentation updates
`docs/TASK_TRACKER.md` row T-001 (status, PR link); `data/README.md` snapshot row.

## 14. Git branch and PR instructions
- Branch: `data/T-001-download-zips` created from the latest `main`
- First commit: this prompt file
- Open a DRAFT PR early; title "T-001: Download all global zips"; fill in `.github/pull_request_template.md`
- Never merge; wait for the Project Lead
- Commit with your own Git identity (D-020)

## 15. Out-of-scope or blocking issues
- The tracker shows T-001 as `TODO`, not `ASSIGNED`. The Lead's team message assigns Member 2 to start with the FIRMS downloads; the Lead should confirm in the tracker.
- The repository checkout lives in OneDrive. `data/raw` is a directory junction to `C:\IgnisLine-data\raw` so ~9.7 GB is not synced to the cloud. Local setup only, not committed.
- T-002 (2026 API) and T-008 (availability) need `FIRMS_MAP_KEY` and have their own branches and PRs.
