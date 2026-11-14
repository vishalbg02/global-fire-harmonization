# CLAUDE.md: Instructions for Claude Code (and any AI assistant)

This repository is the single source of truth. **Do not rely on chat history, account memory or a previous session.** Every teammate may use a different Claude account. Every decision lives in `docs/`.

## Session startup: mandatory, every session, every account

1. Read `CLAUDE.md` (this file).
2. Read `README.md`.
3. Read `docs/HANDOFF.md`.
4. Read `docs/TEAM_ROLES.md`.
5. Read `docs/TASK_TRACKER.md`.
6. Read the documents relevant to the task: `docs/TEAM_WORKFLOW.md`, `docs/ARCHITECTURE.md`, `docs/DATA_CONTRACT.md`, `docs/SCIENTIFIC_METHODOLOGY.md`, `docs/TECH_STACK.md`, `docs/DECISION_LOG.md`.
7. Check Git: `git status`, `git branch --show-current`, `git log --oneline -10`, `gh pr list`.
8. Confirm with the user **who they are** (Member 1, 2 or 3), **which task** (ID from the tracker) and **its boundaries**.
9. If the task is not in the tracker, conflicts with repository decisions, or depends on an unapproved decision: **stop and ask.** Never guess.

## Which role are you assisting?

- **Member 2 (Data & Science) or Member 3 (App & UI):**
  - Work only on a task the Lead has assigned to that member in `docs/TASK_TRACKER.md`.
  - First generate the task prompt (`docs/TEAM_WORKFLOW.md` §4), saved to `docs/task-prompts/`.
  - Then implement only that task on its branch and submit a PR.
- **Member 1 (Project Lead):**
  - Help with planning, task assignment, prompt review and PR review (summaries, diff checks, running tests).
  - Decisions and merges are the Lead's. Merge only when the Lead explicitly instructs it for a specific PR.

## Hard rules

- **Never expand scope.** Do not assign additional work, invent requirements, or start tasks that are not assigned.
- **Approval gates:**
  - Do not change the tech stack, architecture, scientific methodology, data contract or scope without the Lead's approval, recorded in `docs/DECISION_LOG.md`.
  - Out-of-scope needs follow `docs/TEAM_WORKFLOW.md` §6.
- **Git:**
  - Never push to `main`.
  - Never merge a PR.
  - Never approve a PR.
  - Never force-push to shared branches.
  - One branch and one PR per task (`CONTRIBUTING.md`).
- **Scientific honesty:**
  - Hotspots are not fire counts or burned area.
  - Never mark a validation as passed unless it actually ran.
  - Never invent dataset sizes, measurements or performance numbers.
  - Label claims as verified, estimate, assumption or hypothesis.
- **Never interpolate or fabricate observations.** Missing data must be shown as missing or "cannot determine". Synthetic fixtures must be labelled `SYNTHETIC` and never shown as results.
- **Secrets and large files:**
  - Never commit keys, tokens, `.env` files or credentials; use `.env.example`.
  - Never commit NASA raw archives or interim files (`data/raw/`, `data/interim/`). Contract products in `data/products/` go in Git **only through Git LFS** (D-027, `data/README.md`). Run `git lfs install` once per machine.
- Do not change GitHub settings, repository visibility or collaborators.
- **No AI attribution (D-020):**
  - Never put Claude's name, any AI assistant's name, or AI-generated attribution in commit messages, PR titles or descriptions, branch names, code comments, documentation credits or project metadata. That includes `Co-Authored-By` trailers and "Generated with …" lines.
  - Commits use the human contributor's own Git identity. Never change Git identity or impersonate anyone.
  - Check before every commit and every PR.

## Documentation duties (in the same PR as the work)

| Change | Update |
|---|---|
| Task progress | Your task's row in `docs/TASK_TRACKER.md` (only your row) |
| Architecture or interface | `docs/ARCHITECTURE.md`, `docs/DATA_CONTRACT.md` (approval first) |
| Scientific method | `docs/SCIENTIFIC_METHODOLOGY.md` (approval first) |
| Decision | `docs/DECISION_LOG.md` |
| Validation run | `docs/VALIDATION_PLAN.md` (actual results, including failures) |
| Risk or limitation | `docs/RISKS_AND_LIMITATIONS.md` |
| End of a substantial session | `docs/HANDOFF.md`, `docs/PROGRESS_LOG.md` |

Keep this file short. Put details in `docs/`.

## Coding standards (apply once the stack is approved)

- Python: type hints and ruff-clean code. Pure functions for the science, with pytest tests on synthetic data where the answer is known.
- Frontend: TypeScript strict mode. Components consume only the documented data contract.
- Commit messages use Conventional Commits with the task ID, e.g. `feat(api): add /api/meta endpoint (T-034)`.
