# CLAUDE.md: Instructions for Claude Code (and any AI assistant)

This repository is the single source of truth. **Do not rely on chat history, account memory or a previous session.** Every decision lives in `docs/`.

## Resuming work: mandatory every session

1. Read `CLAUDE.md` (this file), then `README.md`.
2. Read `docs/HANDOFF.md` and `docs/TASK_TRACKER.md`.
3. Read the documents relevant to the task: `docs/ARCHITECTURE.md`, `docs/DATA_CONTRACT.md`, `docs/SCIENTIFIC_METHODOLOGY.md`, `docs/DECISION_LOG.md`.
4. Run `git status` and `git log --oneline -15`, and check open PRs (`gh pr list`).
5. Summarize the current state to the user in a few lines.
6. If the next task is not explicitly assigned, **ask the user what to work on.** Never assume.

## Project context (short)

- NASA Space Apps 2026, challenge "Harmonization of MODIS and VIIRS Hot Spots".
- Product: a global harmonized monthly fire-activity record (Jul 2002 → present) built from NASA FIRMS. It uses Aqua MODIS, S-NPP VIIRS and NOAA-20 VIIRS as "witnesses" and gives uncertainty-aware verdicts plus a validation suite. Details: `docs/PROJECT_PLAN.md`.
- Team of three:
  - **Member 1:** Project Lead, approves decisions and merges
  - **Member 2:** data and science
  - **Member 3:** application and UI
  - See `docs/TEAM_ROLES.md`.

## Hard rules

- **Approval gates.** Do not finalize the tech stack, the architecture, the data contract, scientific-method changes or scope changes without the Project Lead's explicit approval. Record approvals in `docs/DECISION_LOG.md`.
- **Scientific honesty:**
  - Hotspots are not fire counts or burned area.
  - Never claim a validation result that has not actually been run.
  - Never invent dataset sizes, measurements or performance numbers.
  - Label every claim as verified, estimate, assumption or hypothesis.
- **Never interpolate or fabricate observations.** Missing data must be shown as missing or "cannot determine".
- Synthetic fixtures must be labelled `SYNTHETIC`. They must never appear in demos or results.
- **Secrets:** never commit API keys, tokens, `.env` files or credentials. Use `.env.example`.
- **Large data:** never commit NASA archives, Parquet products or anything over ~5 MB. They belong in `data/` (git-ignored); see `data/README.md`.
- Do not change repository visibility, collaborators, or GitHub settings.
- **Branching:** never push directly to `main`, and never merge PRs on the Project Lead's behalf. Follow `CONTRIBUTING.md`.

## Documentation duties (update in the same commit/PR as the work)

| Change | Update |
|---|---|
| Task started or finished | `docs/TASK_TRACKER.md` |
| Architecture or interface change | `docs/ARCHITECTURE.md`, `docs/DATA_CONTRACT.md` |
| Scientific-method change | `docs/SCIENTIFIC_METHODOLOGY.md` |
| Important decision | `docs/DECISION_LOG.md` |
| Validation run | `docs/VALIDATION_PLAN.md` (actual results, including failures) |
| New risk or limitation | `docs/RISKS_AND_LIMITATIONS.md` |
| End of a substantial session | `docs/HANDOFF.md` and `docs/PROGRESS_LOG.md` |

Keep this file short. Put details in `docs/`.

## Coding standards (apply once the stack is approved)

- Small, focused PRs, each tied to a task ID in `TASK_TRACKER.md` (e.g. `T-012`).
- Python: type hints and ruff-clean code. Pure functions for the science, with pytest tests on synthetic data where the answer is known.
- Frontend: TypeScript strict mode. Components consume only the documented data contract.
- Data shared between workstreams must conform to `docs/DATA_CONTRACT.md`. Change the contract first, with approval, then the code.
- Commit messages use Conventional Commits (`feat:`, `fix:`, `docs:`, `chore:`, `test:`, `data:`).
