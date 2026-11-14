# Handoff: Current Project State

**Last updated:** 2026-11-14 (planning and repository-setup session)

## Exact current state

- **Phase:** planning complete; **waiting for Project Lead approvals** before any implementation.
- **No application code, no installed dependencies, no data downloaded into the repo.**
- **Repository:** private GitHub repo `global-fire-harmonization` (URL and verification below).

## Completed

- Discovery research, critique and the final direction (Many Witnesses + Witness Stand, global scope). See `RESEARCH_SUMMARY.md`.
- Verified data access: FIRMS global yearly zips, ≈9.1 GB zipped, no login. Column schemas and satellite codes verified (`DATA_SOURCES.md`).
- Full documentation set, `CONTRIBUTING.md`, `.gitignore`, `.env.example`, `data/README.md`.

## In progress

- Nothing.

## Pending: needs the Project Lead

1. **Approve or amend the tech stack** (`TECH_STACK.md`, D-008).
2. **Approve or amend data contract v0.1.0** (`DATA_CONTRACT.md`, D-016).
3. Decide the API owner (D-015) and confirm product direction D-003.
4. Add the two collaborators (Lead only).
5. Decide repo visibility for judges before submission (D-014).

## Can start immediately (independent of the stack decision)

- **T-001 / T-002:** start the global zip downloads and the 2026 API pulls (Member 2 needs a MAP_KEY). These are on the critical path.
- **T-050:** the Lead defines validation case windows.

## Known issues / open questions

- MODIS `version` field varies across years (T-007).
- Aqua's drift onset date and the end of the MODIS mission are unconfirmed (T-008).
- GFED region-mask access is unverified (T-004; fallback exists).
- Local machine has Node 20.20.2 (EOL); Node 22/24 LTS needed.

## Last successful tests

- None. There is no code yet.

## Next recommended actions

1. The Lead reviews `TECH_STACK.md` and `DATA_CONTRACT.md` and approves them (target: H0).
2. Member 2 starts the downloads (T-001, T-002) **right away**.
3. After approval: T-030 (app setup) and T-010 (fixtures).

## Important files

- `CLAUDE.md`: rules for AI assistants
- `docs/PROJECT_PLAN.md`: scope, features, 36-hour schedule
- `docs/TASK_TRACKER.md`: tasks and status
- `docs/DECISION_LOG.md`: approvals

## Repository verification (2026-11-14, via GitHub CLI)

- URL: https://github.com/vishalbg02/global-fire-harmonization
- `visibility: PRIVATE`, `isPrivate: true`, default branch `main`
- Collaborators: owner only (`vishalbg02`). **None added by automation.**
- The initial setup commits were pushed directly to `main` as a one-time bootstrap. **From now on, all changes go through PRs reviewed by the Lead** (`CONTRIBUTING.md`).
