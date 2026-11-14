# Decision Log

Approval status: **APPROVED** (by the Project Lead) · **PROPOSED** (awaiting approval) · **OPEN** (not yet proposed or decided) · **SUPERSEDED**.

| ID | Date | Decision | Status |
|---|---|---|---|
| D-001 | 2026-11-14 | Challenge: Harmonization of MODIS and VIIRS Hot Spots | APPROVED |
| D-002 | 2026-11-14 | Global scope (not selected regions) | APPROVED |
| D-003 | 2026-11-14 | Product direction: Many Witnesses + Witness Stand | APPROVED (implicitly, by proceeding to the global plan; Lead to confirm) |
| D-004 | 2026-11-14 | Historical data from FIRMS global yearly zips; 2026 from the area API | PROPOSED |
| D-005 | 2026-11-14 | Aqua as display scale; drift cutoff measured empirically | PROPOSED |
| D-006 | 2026-11-14 | Harmonized record starts 2002-07; Terra in the raw view only | PROPOSED |
| D-007 | 2026-11-14 | NOAA-21 excluded from the MVP | PROPOSED |
| D-008 | 2026-11-14 | Technology stack | PROPOSED (see `TECH_STACK.md`) |
| D-009 | 2026-11-14 | Regular lat/lon grid; analysis 0.5° (vs 0.25°), fine 0.05°/0.1°: final choice at G1 | PROPOSED / OPEN |
| D-010 | 2026-11-14 | Baseline 2003–2022 + Aqua-only sensitivity test | PROPOSED |
| D-011 | 2026-11-14 | Private GitHub repo; collaborators added by the Lead only | APPROVED |
| D-012 | 2026-11-14 | Git workflow: feature branches, PRs, Lead-only merges | SUPERSEDED by D-017 |
| D-013 | 2026-11-14 | Demo is local-first plus a recorded video; deployment optional | PROPOSED |
| D-014 | — | Repo visibility for judges at submission | OPEN |
| D-015 | — | API owner: Member 3 (recommended if Python-capable) or Member 2 | OPEN |
| D-016 | 2026-11-14 | Data contract v0.1.0 | PROPOSED |
| D-017 | 2026-11-14 | Team workflow: Lead assigns tasks; individual Claude sessions generate task prompts; one branch + PR per task; Lead reviews every PR and alone merges | APPROVED (Lead's instruction); **in effect** since PR #2 merged (2026-11-14) |
| D-018 | 2026-11-14 | Lead bookkeeping commits allowed directly on `main` (tracker, decision log, progress log, handoff only) | PROPOSED |
| D-019 | — | Technical protection of `main` (GitHub Pro branch protection vs policy + local guard) | OPEN |
| D-020 | 2026-11-14 | No AI names or AI-generated attribution in commits, PRs, branch names, code comments, credits or metadata; human Git identity only | APPROVED (Lead's instruction) |
| D-021 | 2026-11-14 | Rewrite the 4 bootstrap commits on `main` to remove AI trailers | APPROVED and DONE (force-pushed 2026-11-14) |

---

### D-001: Challenge selection
- **Context:** NASA Space Apps 2026.
- **Decision:** the "Harmonization of MODIS and VIIRS Hot Spots" challenge.
- **Status:** APPROVED.

### D-002: Global scope
- **Context:** an earlier plan targeted two regions (Australia, Punjab/Haryana) to reduce risk.
- **Alternatives:** two-region app; curated set of regions; global.
- **Decision:** global exploration (any cell, country, continent, custom area), with verdicts only where data are sufficient and transparent coverage.
- **Reasoning:** the product objective set by the Lead. Feasibility checked: the global archive is ≈9.1 GB zipped.
- **Status:** APPROVED by the Project Lead (2026-11-14).

### D-003: Product direction
- **Context:** the first recommendation, "Constant Witness" (a single Aqua reference), was critiqued: the reference is absent in the present, it discards VIIRS detail, its trust grades were subjective, and its validation was not out-of-regime.
- **Alternatives:** Constant Witness; Common Ground (only fires both sensors detect); Homogenization Lab; Many Witnesses.
- **Decision:** Many Witnesses (precision-weighted combination of witnesses with uncertainty) plus the Witness Stand (pre-registered validation, failures published).
- **Status:** APPROVED implicitly. **The Lead should confirm explicitly.**

### D-004: Data acquisition strategy
- **Alternatives:** per-country downloads; the API for all years (exceeds the 5,000-transactions-per-10-minutes limit for 25 years worldwide); the Archive Download tool (queued, needs login); global yearly zips.
- **Decision:** global yearly zips for 2002–2025 (no login, verified) plus the area API for 2026.
- **Status:** PROPOSED.

### D-005: Aqua as display scale, with measured drift
- **Context:** Aqua's orbit is drifting; the onset date is not confirmed.
- **Decision:** express harmonized values on the Aqua-equivalent scale, and remove Aqua from the combination after a cutoff estimated from the data (Aqua/VIIRS ratio trend), to be confirmed at R2.
- **Status:** PROPOSED.

### D-006: Start date and Terra
- **Decision:** the harmonized record starts 2002-07, because Terra-only months would need a second calibration chain and Terra samples the morning. Terra is shown in the raw view only.
- **Status:** PROPOSED.

### D-007: NOAA-21
- **Decision:** excluded from the MVP. It is not in the zips (API only), and NOAA-20 already covers the present.
- **Status:** PROPOSED.

### D-008: Technology stack
- **Status:** PROPOSED. Full comparison in `TECH_STACK.md`. Awaiting Lead approval.

### D-009: Grid
- **Decision (proposed):** a regular lat/lon grid. Analysis 0.5° recommended (more activity per cell, so more determinable verdicts). Fine cell-day grid 0.05° or 0.1°. Final sizes are chosen at G1 by best Aqua vs S-NPP agreement on 2012–2016, before validation.
- **Status:** PROPOSED / OPEN.

### D-010: Baseline
- **Decision (proposed):** 2003–2022, same calendar month, harmonized values. Sensitivity test S1 uses an Aqua-measured baseline (2003–2021).
- **Status:** PROPOSED.

### D-011: Repository
- **Decision:** private GitHub repo `global-fire-harmonization` under the Lead's account. No collaborators are added by automation.
- **Status:** APPROVED.

### D-012: Git workflow
- **Decision:** see `CONTRIBUTING.md`. Branch protection is not available on private repos with GitHub Free, so the "no direct pushes to `main`" rule is enforced by convention.
- **Status:** SUPERSEDED by D-017 (2026-11-14).

### D-013: Demo and deployment
- **Decision:** local-first demo plus a recorded video as the primary artifact. Public deployment is P1.
- **Status:** PROPOSED.

### D-014: Repo visibility for judges
- **Context:** judges may expect a code link. The repo is private.
- **Options:** make it public before submission (Lead action); keep it private and submit without a code link; provide access another way.
- **Status:** OPEN. The Lead decides before H32.

### D-015: API ownership
- **Options:** Member 3 builds the thin API calling Member 2's `harmonize_area()` (recommended, to offload the critical path), or Member 2 builds it.
- **Status:** OPEN. Depends on Member 3's Python comfort.

### D-016: Data contract v0.1.0
- **Status:** PROPOSED. See `DATA_CONTRACT.md`.

### D-017: Three-member team workflow
- **Context:** three members, each possibly using a separate Claude account or session with no shared memory.
- **Decision:**
  - The Lead assigns tasks in `TASK_TRACKER.md`.
  - The teammate's Claude session runs the startup checklist and generates a self-contained task prompt (template in `TEAM_WORKFLOW.md` §4), committed to `docs/task-prompts/`.
  - One branch and one PR per task, with branch prefixes `data/`, `science/`, `frontend/`, `api/`, `fix/` and `docs/`.
  - The Lead reviews every PR (approve / request changes / reject) and alone merges.
  - No teammate or AI session merges, approves or pushes to `main`.
- **Supersedes:** D-012.
- **Status:** APPROVED by the Lead's instruction (2026-11-14). In effect since PR #2 merged (merge commit `cc940ba`).

### D-018: Lead bookkeeping exception
- **Context:** routing every tracker or status update through a PR would slow the Lead down and cause conflicts.
- **Decision (proposed):** the Lead may commit directly to `main` only for `TASK_TRACKER.md`, `DECISION_LOG.md`, `PROGRESS_LOG.md` and `HANDOFF.md`. Everything else goes through PRs.
- **Alternative:** the Lead also uses PRs for bookkeeping (stricter, slower).
- **Status:** PROPOSED.

### D-019: Technical protection of `main`
- **Facts (verified 2026-11-14):** `main` has no branch protection and no rulesets. On a personal-account repository, collaborators get write access, so they can technically push to `main`. Per GitHub's documentation, protected branches and rulesets on private repositories require a paid plan.
- **Options:**
  - (a) GitHub Pro, then protect `main`: require a PR with 1 approval and block force pushes. This costs money.
  - (b) Make the repository public, where protection is free. This conflicts with D-011 (private).
  - (c) Policy plus the local pre-push guard (`.githooks/pre-push`) plus the Lead checking `git log origin/main` at each review.
- **Recommendation:** (c) for the hackathon; (a) if the Lead wants hard enforcement.
- **Status:** OPEN. **No GitHub setting has been changed.**

### D-020: No AI attribution
- **Decision:**
  - Never include Claude's name, any AI assistant's name, or AI-generated attribution in commit messages, PR titles or descriptions, branch names, source code comments, documentation authorship or credits, or project metadata.
  - Commits and PRs use the human contributor's own Git identity and describe the work accurately.
  - Never impersonate a contributor or alter Git identity without authorization.
  - Applies to every teammate and every AI session. Check before each commit and PR. The local `commit-msg` guard helps.
- **Status:** APPROVED by the Lead's instruction (2026-11-14).

### D-021: Clean the bootstrap history on `main`
- **Facts:** the 4 bootstrap commits on `main` (6670a4b, 92afa01, 343a874, 2d26909) contain AI `Co-Authored-By` trailers, and one subject line names the assistant. They were created before D-020.
- **Options:**
  - (a) Rewrite those commits and force-push `main`. Cheapest now, before collaborators clone. Destructive to remote history.
  - (b) Leave the history as is and apply D-020 from now on.
- **Decision:** option (a), approved by the Lead on 2026-11-14.
- **Execution:**
  - The commits were rebuilt with identical file trees and with the original author, committer and dates preserved. Only the messages changed: AI `Co-Authored-By` trailers removed; the tool's name replaced with "assistant instructions".
  - Force-pushed with a lease on the old tip.
  - Mapping: 6670a4b→8daabd3, 92afa01→5c0d8b4, 343a874→348ef2d, 2d26909→00c9f7f.
  - The PR branch was rebased onto the new `main`. GitHub auto-closed PR #1 on the base force-push and would not reopen it, so PR #2 replaces it (same branch).
- **Note:** the *file contents* of those historical commits still contain the old "Claude / M1" owner credit in `TASK_TRACKER.md`. It is corrected going forward by PR #2. Rewriting historical file contents was not part of this decision.
- **Status:** APPROVED and DONE.
