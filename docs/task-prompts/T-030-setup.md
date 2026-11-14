# Task prompt: T-030 Environment setup per the approved stack; app skeleton

> Prepared for: Member 3 · Date: 2026-11-14 · Based on main @ 14a5e35
> Source of truth: docs/TASK_TRACKER.md row T-030. This prompt adds no scope beyond it.
> **Assignment status:** at the time of writing, the tracker row still shows `TODO` with no owner. Member 3 reports that the Lead directed them to start with the application setup and frontend foundation (see §15, item 1). The Lead must set the row to `ASSIGNED` before this work is reviewed.

## 1. Project context

The team is building a global web platform for the NASA Space Apps Challenge 2026, "Harmonization of MODIS and VIIRS Hot Spots" (Many Witnesses + Witness Stand, global scope, D-002/D-003). FIRMS hotspots from three early-afternoon satellites are harmonized by Member 2's pipeline into one monthly record; Member 3 builds the API and web app around those products (`docs/PROJECT_PLAN.md`). T-030 is the first application task: it creates the runnable web-app skeleton in `app/` that every later frontend task (T-031 onward) builds on.

## 2. Task objective

When the task is done, a clean clone can install and run a React + Vite + strict-TypeScript app from `app/` with the approved frontend libraries installed and pinned in a lockfile, an agreed folder structure, Vitest configured with a passing smoke test, and written setup/run instructions. The app shows only a placeholder shell. It contains no map, calendar, charts, API calls or contract data yet.

## 3. Assigned responsibility

- Task ID / priority: T-030 / P0
- Owner: Member 3 (Application Development & UI)
- Reviewer and merger: Member 1 (Project Lead)
- Dependencies (must be MERGED first): T-0A, T-0D (both DONE in the tracker)

## 4. Relevant files and directories

- Read: `CLAUDE.md`, `README.md`, `docs/HANDOFF.md`, `docs/TEAM_ROLES.md`, `docs/TASK_TRACKER.md`, `docs/TEAM_WORKFLOW.md`, `docs/TECH_STACK.md` (§7), `docs/ARCHITECTURE.md`, `docs/DATA_CONTRACT.md`, `docs/DECISION_LOG.md`, `docs/prompts/MEMBER_3_APPLICATION_PROMPT.md` (§0, §3, §5, §18, §19), `.gitignore`, `.env.example`, `CONTRIBUTING.md`
- Create/modify:
  - `app/` (new; everything for the web app, including `package.json`, lockfile, Vite and TypeScript config, `src/`, `public/`, and `app/README.md`)
  - `docs/task-prompts/T-030-setup.md` (this file)
  - `docs/TASK_TRACKER.md` (the T-030 row only)
  - `.gitignore` only if `node_modules`/build output are not already ignored (to be checked; see §15)

## 5. Approved technologies

From `docs/TECH_STACK.md` §7 (approved 2026-11-14, D-008). Versions are those of the latest release at approval; pin exact versions in the lockfile at setup.

- React 19 + Vite 8 + TypeScript, **strict mode** (TypeScript version pinned by the Vite template)
- MapLibre GL JS 6 + deck.gl 9 (installed only; not used in this task)
- terra-draw (installed only)
- Apache ECharts 6 (installed only)
- TanStack Query (installed and the provider mounted, with no queries)
- Vitest (tests)
- Runtime: Node.js 22.12+ or 24 LTS. Verified locally: Node v24.19.0, npm 11.17.0.

Nothing outside this list may be added without a new Lead decision.

## 6. Architecture and data contract

- Component: the web app (`docs/ARCHITECTURE.md` §2). It will talk only to the API or the static JSON export, and never reads Parquet.
- Directory layout (approved, D-023): web app in `app/`; API in `api/` (not part of this task); never write in `pipeline/`.
- Data contract: `contract_version 0.1.0` (D-016). T-030 consumes **no** contract data. Contract TypeScript types belong to later tasks (T-031 onward).

## 7. Inputs

- None from Member 2 (no fixtures needed; T-010 is not a dependency).
- Environment variables: none. If one is later needed, only its name goes in `.env.example`; never values.

## 8. Expected outputs

1. `app/` containing a Vite React + TypeScript project that builds and runs locally.
2. `app/package.json` and a committed lockfile with exact versions of every stack library listed in §5.
3. Strict TypeScript config (`"strict": true`).
4. The folder structure proposed in the Member 3 prompt §5, created with placeholder/empty-state files only where needed: `src/api/`, `src/state/`, `src/components/` (`map`, `calendar`, `charts`, `evidence`, `anomalies`, `export`, `common`), `src/content/`, `public/geo/`. Empty folders are kept only if the Lead approves (see §15).
5. A placeholder shell page with the project name and a short statement that views are added in later tasks. No data, charts or invented numbers.
6. TanStack Query provider mounted at the app root.
7. Vitest configured, with at least one smoke test that renders the shell.
8. Scripts in `package.json`: `dev`, `build`, `test`, and a type-check command.
9. `app/README.md`: prerequisites, install, run, build and test commands, folder map.

## 9. Implementation requirements

1. Create the project from the official Vite React + TypeScript template, then install only the §5 libraries.
2. Enable TypeScript strict mode; the build must pass type-checking.
3. Pin exact versions via the lockfile; record the installed versions in the PR description.
4. Do not add map, chart, drawing or data-fetching code. These libraries are installed and verified to import, nothing more.
5. No science, no synthetic data, no fixture usage in this task.
6. Do not use `any` to silence type errors.
7. Keep the shell accessible by default (landmark elements, a page title, visible focus), without going beyond the skeleton.

## 10. Constraints: do not modify

- Do not change the tech stack, architecture, scientific methodology or data contract.
- Do not edit files outside §4 "Create/modify".
- Do not touch `pipeline/`, `data/`, `api/`, `docs/DATA_CONTRACT.md`, `docs/ARCHITECTURE.md`, `docs/TECH_STACK.md` or the root `README.md` (README changes need Lead approval first).
- No secrets, no `.env` files, no `node_modules`, no build output, no data products committed.
- No direct pushes to `main`; no self-merge; wait for the Project Lead.
- No AI tool names or attribution in commits, PR text, branch names, code comments, `package.json` fields or other metadata (D-020).
- Do not mark anything as validated that has not been run. Report real command output only.

## 11. Acceptance criteria

From the tracker: **"Runs locally for M1 and M3."** Made measurable:

1. From a clean clone, `cd app && npm ci` completes without errors on Node 22.12+ or 24.
2. `npm run dev` serves the shell, which loads in a browser with no console errors.
3. `npm run build` succeeds, including the strict type-check.
4. `npm test` passes, with the smoke test among the tests run.
5. `app/package.json` lists every §5 library, and the lockfile is committed.
6. `tsconfig` has `strict: true`.
7. `app/README.md` lets the Lead (Member 1) run the app by following it alone. The Lead's own run is the confirmation; this PR cannot claim it.
8. No files outside §4 are changed.

## 12. Required tests

Run from `app/`; paste the actual output summary into the PR.

- `npm ci`
- `npm run build` (includes the type-check)
- `npm test`
- Manual: `npm run dev`, open the page, check the browser console for errors, take a screenshot.

## 13. Documentation updates

- `docs/TASK_TRACKER.md`: the T-030 row only (status, branch, PR link).
- `app/README.md`: setup and run instructions (new file inside `app/`).
- Root `README.md` "Setup": **not edited**; a pointer is proposed to the Lead in the PR (approval first).
- `docs/HANDOFF.md` and `docs/PROGRESS_LOG.md`: a PR note asking the Lead to update them, unless the Lead says otherwise.

## 14. Git branch and PR instructions

- Branch: the tracker plans `frontend/T-030-setup`. Member 3's local branch is currently `Swastik` (name requested by the Lead; see §15, item 2). It has not been pushed.
- First commit: this prompt file.
- Open a DRAFT PR early; title "T-030: Environment setup per the approved stack; app skeleton"; fill in `.github/pull_request_template.md`.
- Mark Ready for review only when §11 and §12 are satisfied.
- Never merge; wait for the Project Lead.
- Commit with your own Git identity; no AI names or attribution in commits, PR text or branch names (D-020). Conventional Commits with the task ID, e.g. `feat(app): scaffold app skeleton (T-030)`.

## 15. Out-of-scope or blocking issues

Open questions for the Lead. None is decided here.

1. **Assignment is not recorded.** The tracker row T-030 is `TODO` with no owner. `CLAUDE.md` and the Member 3 prompt require `ASSIGNED` before work. Please update the row.
2. **Branch name.** `Swastik` differs from the tracker's `frontend/T-030-setup` and from the one-branch-per-task convention (`CONTRIBUTING.md` §2). Please confirm the name, or have it renamed before the push.
3. **Scope of "environment setup".** The tracker says "Environment setup per the approved stack; app skeleton". This prompt covers `app/` only. Is Python/API environment setup (`api/`, `requirements.txt`, venv) part of T-030, or left to T-034? The local Python is 3.15.2, outside the approved 3.12–3.14 range.
4. **Empty folders.** Git does not track empty folders. Should the Member 3 prompt §5 structure be created now with placeholder files, or each folder added when its task starts?
5. **Setup docs location.** The Member 3 prompt says the root `README.md` "Setup" needs approval first. This prompt uses `app/README.md` and proposes a pointer in the root README. Is that acceptable?
6. **Lint/format tooling.** The approved stack lists ruff (Python) and Vitest (frontend) but no frontend linter or formatter. The template's default ESLint config comes with the Vite scaffold. Keep it, or remove it?
7. **Banner.** The persistent "SYNTHETIC DATA — not NASA observations" banner needs `metadata.synthetic` from the API. It is left to T-031 onward, not T-030.

### Lead answers (PR #5 comment)

1. T-030 will be set to `ASSIGNED` (owner Member 3) by the Lead.
2. `Swastik` is accepted for this task only; later tasks use `frontend/T-0XX-<short-name>` or `api/...`.
3. T-030 covers `app/` only. Python/API setup belongs to T-034 (install Python 3.13 or 3.14 first).
4. No placeholder folders; each folder is added when its task starts.
5. `app/README.md` is approved; the root README pointer is proposed in the PR for review.
6. Keep the Vite template's default lint config as-is.
7. The synthetic-data banner is deferred to T-031.
