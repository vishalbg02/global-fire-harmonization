# Handoff: Current Project State

**Last updated:** 2026-11-14 (team-workflow documentation session)

## Exact current state

- **Phase:** planning complete; **waiting for Project Lead approvals** before any implementation.
- **No application code, no installed dependencies, no data downloaded into the repo.**
- **Repository:** private GitHub repo `global-fire-harmonization` (URL and verification below).

## Completed

- Discovery research, critique and the final direction (Many Witnesses + Witness Stand, global scope). See `RESEARCH_SUMMARY.md`.
- Verified data access: FIRMS global yearly zips, ≈9.1 GB zipped, no login. Column schemas and satellite codes verified (`DATA_SOURCES.md`).
- Full documentation set, `CONTRIBUTING.md`, `.gitignore`, `.env.example`, `data/README.md`.

## In progress

- **T-0E, team workflow documentation.** Branch `docs/team-workflow`, PR open and awaiting the Lead's review. It adds `docs/TEAM_WORKFLOW.md`, `docs/task-prompts/`, `.github/pull_request_template.md` and `.githooks/pre-push`, and updates `CLAUDE.md`, `CONTRIBUTING.md`, `TEAM_ROLES.md`, `TASK_TRACKER.md` and this file.

## Pending: needs the Project Lead

1. **Review and merge the team-workflow PR** (D-017, D-018).
2. **Approve or amend the tech stack** (`TECH_STACK.md`, D-008).
3. **Approve or amend data contract v0.1.0** (`DATA_CONTRACT.md`, D-016).
4. Decide the API owner (D-015) and confirm product direction D-003.
5. Add the two collaborators (Lead only).
6. Decide on technical protection of `main` (D-019) and repo visibility for judges (D-014).
7. ~~Rewrite the bootstrap commits on `main` (D-021)~~: done 2026-11-14. Anyone who cloned before this must re-clone or run `git fetch && git reset --hard origin/main` on `main`.

## Recommended for the Lead to assign first (stack-independent)

These are recommendations only; nothing is assigned until the Lead updates `TASK_TRACKER.md`.
- **T-001 / T-002** (Member 2): global zip downloads and 2026 API pulls. Critical path; needs a MAP_KEY.
- **T-050** (Lead): define the validation case windows.

## How to resume work

### As a teammate (Member 2 or 3) in your own Claude session
1. `git switch main && git pull`.
2. Enable the local guards once per clone: `git config core.hooksPath .githooks` (blocks pushes to `main` and AI attribution in commit messages).
3. Start Claude Code in the repository and tell it: *"I am Member <n>. My assigned task is T-XXX."*
4. Claude runs the startup checklist (`CLAUDE.md`), confirms the task and its boundaries, and generates the task prompt into `docs/task-prompts/`.
5. Follow `docs/TEAM_WORKFLOW.md`: task branch, draft PR, implement, tests, docs, ready for review. Then wait for the Lead.
6. If your task isn't in `TASK_TRACKER.md` as `ASSIGNED` to you, stop and ask the Lead.

### As a new Claude session (any account)
- Assume no prior knowledge. Run the `CLAUDE.md` startup checklist, summarize the state from this file and the tracker, and ask the user which task to work on if none is explicitly assigned.

### As the Project Lead
- Check open PRs (`gh pr list`), the tracker, and `git log origin/main` (to spot any unreviewed direct pushes).
- Assign the next tasks in the tracker. Review with the `CONTRIBUTING.md` checklist. Merge personally.

## Known issues / open questions

- MODIS `version` field varies across years (T-007).
- Aqua's drift onset date and the end of the MODIS mission are unconfirmed (T-008).
- GFED region-mask access is unverified (T-004; fallback exists).
- Local machine has Node 20.20.2 (EOL); Node 22/24 LTS needed.

## Last successful tests

- None. There is no code yet.

## Next recommended actions

All of these are the Lead's actions. Teammates start work only on tasks assigned in the tracker.
1. Review and merge the team-workflow PR.
2. Review and approve `TECH_STACK.md` and `DATA_CONTRACT.md` (target: H0).
3. Assign T-001 and T-002 to Member 2 as early as possible (stack-independent, critical path).
4. After stack approval, assign T-030 (app setup, Member 3) and T-010 (fixtures, Member 2).

## Important files

- `docs/TEAM_WORKFLOW.md`: the process from assignment to merge
- `CLAUDE.md`: rules for AI assistants
- `docs/PROJECT_PLAN.md`: scope, features, 36-hour schedule
- `docs/TASK_TRACKER.md`: tasks and status
- `docs/DECISION_LOG.md`: approvals

## Repository verification (2026-11-14, via GitHub CLI)

- URL: https://github.com/vishalbg02/global-fire-harmonization
- `visibility: PRIVATE`, `isPrivate: true`, default branch `main`
- Collaborators: owner only (`vishalbg02`). **None added by automation.**
- The initial setup commits were pushed directly to `main` as a one-time bootstrap. **From now on, all changes go through PRs reviewed by the Lead** (`CONTRIBUTING.md`). The only exception is the Lead's bookkeeping commits (D-018).
- Branch protection: **not configured** on `main`, and there are no rulesets (verified via the API, 2026-11-14). The PR rule is policy, not a technical lock. See `TEAM_WORKFLOW.md` §10 and D-019.
