# Progress Log

Newest entries first. Record completed work, pending work, blockers and decisions.

## 2026-11-15: Build, validation, UI round, acceptance (H0+26)

**Completed (all merged through PRs reviewed by the Lead):**
- Real products for 2002-07 to 2026-11 (method 0.1.0, contract 0.1.1), with the Jammu and Kashmir cells counted by India's official boundary (D-033) and the world named "World".
- Validation: 38 results, 18 PASS, 18 FAIL, 2 INCONCLUSIVE; v0.2 was not adopted (D-030); every failure is in the plan, the risks register and the app.
- App:
  - new design with the verdict above the fold
  - map UX and faster month switching
  - NASA GIBS Blue Marble, satellite view and globe (D-032)
  - India's official boundary
  - stories and How to read
  - Analytics with compare and per-country coverage
  - month picker
  - methods redesign
  - responsive and accessibility work
  - offline copy
- Checks: contract check conforms; number check 0 mismatches (6,492,028 values); about 1,500 automated tests pass.
- Lead: T-080 mock approval; T-081 browser acceptance (Chromium; Safari and Firefox not run); T-060 demo script; T-062 project page draft; T-082 this log and the handoff.

**Decisions:** D-028 Amendment A, D-029, D-030 (not adopted), D-031, D-032, D-033.

**Pending (Lead):** T-061 video, T-062 posting, T-063 submit, T-064 repo visibility (recommend public), T-0F protect `main`, the full offline copy on the demo laptop.

**Optional:** T-093 UI and UX excellence pass (#99).

## 2026-11-14: Teammate workstream prompts (T-0G)

**Completed**
- Read-only audit of PR #2 and the repository: PR #2 merged as `cc940ba`; protected docs unchanged; history clean on `main`.
- Added `docs/prompts/MEMBER_2_DATA_SCIENCE_PROMPT.md` and `docs/prompts/MEMBER_3_APPLICATION_PROMPT.md`. They are self-contained and share an identical integration-handoff section (verified byte-identical). Field names were cross-checked against `DATA_CONTRACT.md`.
- Tracker: stack-dependent tasks marked `BLOCKED (D-008)`, fixtures `BLOCKED (D-016)`, API tasks also blocked on D-015/T-0D. T-0E set to `MERGED`.
- Fixed stale statuses in `HANDOFF.md` and `DECISION_LOG.md` (D-017 in effect; PR #1 → PR #2 reference).

- **D-008 (stack) and D-016 (contract v0.1.0) approved by the Lead at 12:26 IST (H0).** Recorded in `TECH_STACK.md` (§7 final table), `DATA_CONTRACT.md`, `DECISION_LOG.md`, the tracker (34 tasks moved from approval blocks to `BLOCKED (T-0D)`) and both prompts. The contract additions from the prompts were logged separately as D-022 (proposed).

- **T-0D and D-015 approved:** layout `pipeline/` / `api/` / `app/` (D-023); Member 3 owns the API. All tracker blocks removed.

**Pending (Lead):** merge PR #4; decide D-022; assign T-001, T-002, T-008, T-010 (Member 2) and T-030 (Member 3).

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
