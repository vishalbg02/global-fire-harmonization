# Handoff: Current Project State

**Last updated:** 2026-11-14 (teammate-prompts session, T-0G)

## Exact current state

- **Phase:** planning complete. **Stack (D-008) and data contract v0.1.0 (D-016) approved on 2026-11-14 at 12:26 IST (= H0 of the 36-hour schedule; submission target H34 ≈ 2026-11-15 22:26 IST, deadline 23:59 local).**
- **Layout approved (D-023):** `pipeline/` (Member 2), `api/` and `app/` (Member 3). **Member 3 owns the API (D-015).** Nothing blocks code; tasks need only Lead assignment.
- **No application code, no installed dependencies, no data downloaded into the repo.**
- **Repository:** private GitHub repo `global-fire-harmonization` (URL and verification below).

## Completed

- Discovery research, critique and the final direction (Many Witnesses + Witness Stand, global scope). See `RESEARCH_SUMMARY.md`.
- Verified data access: FIRMS global yearly zips, ≈9.1 GB zipped, no login. Column schemas and satellite codes verified (`DATA_SOURCES.md`).
- Full documentation set, `CONTRIBUTING.md`, `.gitignore`, `.env.example`, `data/README.md`.
- **T-0E team workflow**: merged into `main` as PR #2 (merge commit `cc940ba`). D-017 and D-020 are in effect.
- **D-021**: bootstrap history on `main` rewritten without AI trailers.

## In progress

- **T-0G, teammate workstream prompts.** Branch `docs/T-0G-teammate-prompts`, PR awaiting the Lead's review. It adds `docs/prompts/MEMBER_2_DATA_SCIENCE_PROMPT.md` and `docs/prompts/MEMBER_3_APPLICATION_PROMPT.md`, marks stack- and contract-dependent tasks `BLOCKED` in the tracker, and fixes statuses left stale after PR #2 merged.

## Pending: needs the Project Lead

1. **Review the T-0G teammate-prompts PR**, and decide D-018 (Lead bookkeeping commits).
2. ~~Approve the tech stack (D-008)~~: approved 2026-11-14.
3. ~~Approve data contract v0.1.0 (D-016)~~: approved 2026-11-14. **Decide D-022** (the [PROPOSED ADDITION] items in the prompts' shared section).
4. ~~Directory layout and API owner~~: approved 2026-11-14 (D-023, D-015). Confirm product direction D-003.
5. Add the two collaborators (Lead only).
6. Decide on technical protection of `main` (D-019) and repo visibility for judges (D-014).
7. ~~Rewrite the bootstrap commits on `main` (D-021)~~: done 2026-11-14. Anyone who cloned before this must re-clone or run `git fetch && git reset --hard origin/main` on `main`.

## Recommended for the Lead to assign first (stack-independent)

These are recommendations only; nothing is assigned until the Lead updates `TASK_TRACKER.md`.
- **T-001 / T-002** (Member 2): global zip downloads and 2026 API pulls. Critical path; needs a MAP_KEY.
- **T-050** (Lead): define the validation case windows.

## Teammate prompts (start here as Member 2 or 3)

| Member | Prompt | What they can do first |
|---|---|---|
| Member 2 | [`docs/prompts/MEMBER_2_DATA_SCIENCE_PROMPT.md`](prompts/MEMBER_2_DATA_SCIENCE_PROMPT.md) | Once the Lead assigns them: **T-001** (global zip downloads), **T-002** (2026 API pull; needs a MAP_KEY), **T-008**. Then **T-010** fixtures (generator in `pipeline/`) and T-003 onward |
| Member 3 | [`docs/prompts/MEMBER_3_APPLICATION_PROMPT.md`](prompts/MEMBER_3_APPLICATION_PROMPT.md) | Fully unblocked once assigned: **T-030** setup first (`app/`), then T-031–T-033 on fixtures; T-034 API in `api/` |

Paste the whole file (below its separator line) into a fresh Claude Code session at the repository root. Both prompts contain an identical "Shared integration handoff" section. If the two copies ever differ, stop and tell the Lead.

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
- **Lead-authored PRs cannot get a GitHub "Approve" review** (GitHub blocks self-approval). `TEAM_WORKFLOW.md` §8 requires an approved review, so Lead-authored PRs need a documented alternative (Lead decision; not yet written into the workflow).
- **GitHub's Copilot reviewer bot is auto-requested on PRs** (it posted on #1 and #2). This is a GitHub setting; it was not changed. The Lead decides whether to keep it.
- **The pre-rewrite history is still reachable** via closed PR #1 (`refs/pull/1/head`, read-only, GitHub-managed). Only GitHub Support can purge it.
- The merged branch `docs/team-workflow` has not been deleted (Lead action).

## Last successful tests

- None. There is no code yet.

## Next recommended actions

All of these are the Lead's actions. Teammates start work only on tasks assigned in the tracker.
1. Review and merge the T-0G teammate-prompts PR.
2. ~~Decide T-0D and D-015~~: approved.
3. Assign T-001, T-002 and T-008 to Member 2 now (critical path; no code directory needed).
4. Assign T-030 (app setup, Member 3) and T-010 (fixtures, Member 2) now.

## Important files

- `docs/TEAM_WORKFLOW.md`: the process from assignment to merge
- `docs/prompts/`: the Member 2 and Member 3 workstream prompts
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
