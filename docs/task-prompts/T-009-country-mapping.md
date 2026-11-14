# Task prompt: T-009 FIRMS country name to ISO3 / continent mapping

> Prepared for: Member 2 · Date: 2026-11-14 · Based on main @ 87d97a5
> Source of truth: docs/TASK_TRACKER.md row T-009. This prompt adds no scope beyond it.

## 1. Project context
NASA Space Apps Challenge 2026 team project (Many Witnesses + Witness Stand): harmonize NASA FIRMS hotspot detections from several satellites (`docs/PROJECT_PLAN.md`). FIRMS archive detections carry only a country name taken from the file name (for example `Democratic_Republic_of_the_Congo`). The contract uses ISO 3166-1 alpha-3 country codes and continent codes (`cells.country_iso3`, `cells.continent`, entity IDs), so the names must be mapped.

## 2. Task objective
A committed table `pipeline/country_map.csv` maps every FIRMS country name found in the normalized detections (238 distinct names from T-003) to an ISO3 code and a continent code (`AF`, `AN`, `AS`, `EU`, `NA`, `OC`, `SA`). 100% of country files are mapped. Every name the automatic match could not resolve is listed and resolved explicitly in the table, with a note. Nothing is guessed silently.

## 3. Assigned responsibility
- Task ID / priority: T-009 / P0
- Owner: Member 2 (Data Engineering & Scientific Analysis)
- Reviewer and merger: Member 1 (Project Lead)
- Dependencies (must be MERGED first): T-003 (merged)

## 4. Relevant files and directories
- Read: the assistant instructions file at the repository root, `docs/DATA_SOURCES.md` §6, `docs/DATA_CONTRACT.md` (`cells`, entity IDs), `docs/prompts/MEMBER_2_DATA_SCIENCE_PROMPT.md` §7 and §S.3
- Create/modify:
  - `docs/task-prompts/T-009-country-mapping.md` (this file)
  - `pipeline/country_mapping.py` (builder and checker; standard library plus DuckDB)
  - `pipeline/country_map.csv` (the mapping, committed)
  - `pipeline/tests/test_country_mapping.py`
  - `docs/DATA_SOURCES.md` (§6, source of the codes)
  - `docs/TASK_TRACKER.md` (row T-009 only)

## 5. Approved technologies
Python and DuckDB (D-008). Natural Earth admin-0 countries (public domain) is already listed in `docs/DATA_SOURCES.md` §6 and is used only as a reference list to cross-check names, ISO3 codes and continents.

## 6. Architecture and data contract
No contract product is changed. Codes follow the proposed entity ID scheme in the Member 2 prompt §S.3: ISO3 uppercase, continents `AF/AS/EU/NA/OC/SA` (`AN` because the data has detections in Antarctica).

## 7. Inputs
- Distinct `country_name` values in `data/interim/detections/` (T-003, local).
- `ne_50m_admin_0_countries.zip` from https://naciscdn.org/naturalearth/50m/cultural/ (799,734 bytes, SHA-256 `5fed433373581fa648920435f937d95f2d3c0200e067409c6478dcdf1b853139`), downloaded locally with Member 2's approval, only its attribute table is read, never committed.

## 8. Expected outputs
`pipeline/country_map.csv` with columns `firms_name, iso3, continent, method, note`; `method` is `NATURAL_EARTH` (matched by name, code and continent taken from Natural Earth) or `MANUAL` (resolved by hand, with a `note` saying why).

## 9. Implementation requirements
1. Names are the file-name country with underscores replaced by spaces, exactly as stored by T-003.
2. Match against Natural Earth names (name, long name, admin name, formal name, English name, sovereignty) after normalizing case, accents, hyphens and apostrophes. A name that matches more than one country is a conflict and must be resolved manually.
3. Unmatched names, and codes Natural Earth leaves undefined (`-99`), are resolved by hand in an explicit table in the script, each with a note.
4. Continent follows the Natural Earth `CONTINENT` field. Where it says "Seven seas (open ocean)", the UN M49 region of the territory is used and noted.
5. ISO3 codes must be unique per name and match `^[A-Z]{3}$`. Kosovo has no ISO 3166-1 code; the user-assigned code `XKX` is used and flagged.
6. A check compares the table with the data and fails if any name is unmapped, or if the table has names that do not occur in the data.

## 10. Constraints: do not modify
- Do not change the tech stack, architecture, scientific methodology or data contract.
- Do not edit files outside §4 "Create/modify". Do not touch `api/` or `app/`.
- No secrets, no large files, no direct pushes to `main`, no self-merge.
- Do not rewrite or drop detection rows; country names stay as stored. No filtering (T-005).

## 11. Acceptance criteria
100% of country files mapped.

## 12. Required tests
`python -m pytest pipeline/tests/test_country_mapping.py -q`: table structure; unique ISO3 per name where expected; spot checks (Cote d Ivoire = CIV, Republic of Congo = COG vs Democratic Republic of the Congo = COD, Dem Rep Korea = PRK vs Republic of Korea = KOR, Swaziland = SWZ, Kosovo = XKX); conflict detection on a synthetic reference table; and, when the local data exists, that every name in the detections is mapped. `ruff` passes on the files of this task.

## 13. Documentation updates
`docs/TASK_TRACKER.md` row T-009; `docs/DATA_SOURCES.md` §6 (the code source and the decisions flagged for the Lead).

## 14. Git branch and PR instructions
- Branch: `data/T-009-country-mapping` created from the latest `main`
- First commit: this prompt file
- Open a DRAFT PR early; title "T-009: FIRMS country name to ISO3 / continent mapping"; fill in `.github/pull_request_template.md`
- Never merge; wait for the Project Lead
- Commit with your own Git identity (D-020)

## 15. Out-of-scope or blocking issues
- Continent policy for transcontinental countries and ocean territories, and the code `XKX` for Kosovo, are proposals for the Lead (needs Lead approval).
- Disputed or special territories (Palestine, Taiwan, Hong Kong, Kosovo, Western Sahara if present) are mapped by the codes in common use; this is not a political statement.
- A new FIRMS name in a later download would fail the check and need a table row.
