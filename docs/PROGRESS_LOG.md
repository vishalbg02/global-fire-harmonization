# Progress Log

Newest entries first. Record completed work, pending work, blockers and decisions.

## 2026-11-14: Team workflow documentation (T-0E)

**Completed**
- Added `docs/TEAM_WORKFLOW.md`: the process from assignment to merge, the task prompt template, review outcomes, and policy vs actual GitHub protection.
- Added `docs/task-prompts/`, `.github/pull_request_template.md` and `.githooks/pre-push` (local guard, tested: it blocks pushes to `main`, allows task branches, and allows `main` only with `ALLOW_MAIN_PUSH=1`).
- Updated `CLAUDE.md`, `CONTRIBUTING.md`, `TEAM_ROLES.md`, `TASK_TRACKER.md` (Branch/PR/Review columns), `HANDOFF.md`, `DECISION_LOG.md` (D-017 to D-019) and `README.md`.
- Verified: `main` has no branch protection and no rulesets. No GitHub settings were changed.

- Applied the Lead's no-AI-attribution rule (D-020): removed AI authorship credits from docs, added the rule to the workflow docs and PR template, and added a `.githooks/commit-msg` guard (tested: it blocks AI trailers and tool names, allows normal messages). This branch's commits were recreated without AI trailers before the PR was opened.

- D-021 approved and executed: the 4 bootstrap commits on `main` were rebuilt without AI trailers (identical trees; authorship and dates preserved), `main` was force-pushed with a lease, and the branch was rebased onto it. GitHub auto-closed PR #1 on the base force-push; PR #2 replaces it.

**Pending (Lead):** review and merge this PR; decide D-018 and D-019.

## 2026-11-14: Planning and repository setup

**Completed**
- Read the challenge statement. Researched NASA FIRMS, sensor status, harmonization literature and competing 2026 team repos (summary in `RESEARCH_SUMMARY.md`).
- Product discovery: 19 concepts scored. Then a critical review replaced "Constant Witness" with **Many Witnesses + Witness Stand** (D-003).
- Lead decision: **global scope** (D-002).
- Verified the global data access route and measured sizes: FIRMS global yearly zips, ≈9.1 GB zipped, no login (D-004).
- Created planning documentation, contribution workflow, `.gitignore`, `.env.example` and `data/README.md`.
- Initialized Git and created the private GitHub repository https://github.com/vishalbg02/global-fire-harmonization. Visibility verified as PRIVATE; no collaborators added.

**Pending (needs Lead approval)**
- Tech stack (D-008), data contract (D-016), API owner (D-015), repo visibility for judges (D-014).

**Blockers**
- None technical. Implementation waits on stack approval.

**Decisions made**
- D-001, D-002, D-011 approved. Others proposed (see `DECISION_LOG.md`).
