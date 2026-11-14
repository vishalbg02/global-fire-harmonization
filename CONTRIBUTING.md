# Contributing

This is a three-person team with **one rule above all: every task goes through a Pull Request, and only the Project Lead merges into `main`.** The full process, from assignment to merge, is in [`docs/TEAM_WORKFLOW.md`](docs/TEAM_WORKFLOW.md).

## 1. Before you start

- Work only on a task assigned to you in `docs/TASK_TRACKER.md` (status `ASSIGNED`, with you as owner).
- Your Claude session runs the startup checklist (`CLAUDE.md`) and generates the task prompt (`docs/TEAM_WORKFLOW.md` §4).
- Enable the local push guard once per clone:
  ```bash
  git config core.hooksPath .githooks
  ```

## 2. Branches

- `main`: stable and reviewed. **Nobody pushes to it directly.** Only the Lead merges, except for the Lead's bookkeeping commits (D-018).
- One branch per task, created from the latest `main`. Use the name in the task's tracker row:

| Prefix | Use |
|---|---|
| `data/` | Data acquisition and processing |
| `science/` | Calibration, uncertainty, verdicts, validation |
| `frontend/` | Web application UI |
| `api/` | API endpoints |
| `fix/` | Bug fixes |
| `docs/` | Documentation-only changes |

Format: `<prefix>/T-XXX-<short-name>`, e.g. `data/T-003-normalize` or `frontend/T-031-global-map`.

```bash
git switch main && git pull
git switch -c data/T-003-normalize
```

## 3. Commits

Use Conventional Commits and include the task ID:

```
feat(frontend): render analysis-cell layer for selected month (T-031)
fix(science): exclude outage months from baseline percentiles (T-014)
data: add SYNTHETIC fixtures for contract v0.1.0 (T-010)
docs: add task prompt for T-003
```

Types: `feat`, `fix`, `docs`, `test`, `data`, `chore`, `refactor`. Keep commits small and focused.

### Attribution rule (D-020): applies to every teammate and every AI session

- **Never** include Claude's name, any AI assistant's name, or AI-generated attribution in:
  - commit messages, including `Co-Authored-By` trailers and "Generated with …" lines
  - PR titles or descriptions
  - branch names
  - code comments
  - documentation credits
  - project metadata
- Commit with **your own** Git identity (`git config user.name` / `user.email`). Never change identity or impersonate another contributor.
- Commit messages must describe the actual work performed.
- Before each commit or PR, check that no AI names or attribution are included. The local `commit-msg` guard (enabled by `core.hooksPath .githooks`) blocks common AI trailers and tool names.
- When a commit touches the assistant instructions file at the repository root, call it "assistant instructions" in the message instead of using its file name. The guard rejects the name.

## 4. Pull Requests

1. The first commit on the branch is the task prompt (`docs/task-prompts/T-XXX-*.md`).
2. Push and open a **draft PR** against `main` early. Title: `T-XXX: <title>`.
3. Implement only the assigned task. Run the required tests. Update docs **in the same PR**, including **only your own row** in `TASK_TRACKER.md`.
4. Fill in the PR template (`.github/pull_request_template.md`):
   - summary
   - changed files
   - tests run, with results
   - documentation updated
   - limitations
   - scope issues
   - screenshots (UI)
5. Mark the PR *Ready for review* and set your tracker status to `IN_REVIEW`.
6. **Wait for the Project Lead.**
   - If changes are requested, fix them **in the same PR** and re-request review.
   - Never merge your own PR. Never approve PRs. AI sessions never merge or approve.

## 5. Project Lead review checklist

- [ ] Task requirements fulfilled (prompt plus tracker acceptance criteria)
- [ ] Follows the approved architecture
- [ ] Respects the data contract (fields, types, enums, `contract_version`)
- [ ] Scientific calculations and interpretations are correct; no unsupported or unvalidated claims
- [ ] Code is readable and maintainable
- [ ] Appropriate tests were run, with results shown
- [ ] Errors and edge cases handled (nulls, outages, zero baselines, no detections, provisional months)
- [ ] Integrates with the other workstream
- [ ] Documentation updated
- [ ] No secrets, `.env` files or credentials; no raw/interim data; products only through Git LFS (D-027)
- [ ] No regressions

**Outcomes:**
- **Approved:** the Lead merges personally (squash and merge, then deletes the branch).
- **Changes requested:** fix in the same PR.
- **Rejected:** the PR is closed and the task reconsidered.

Details are in `docs/TEAM_WORKFLOW.md` §7–8.

## 6. Out-of-scope changes

Anything outside your task needs the Lead's approval. That includes the stack, architecture, methodology, data contract and the other workstream's files.

Stop, describe it under "Scope issues" in the PR, set your task to `BLOCKED` if needed, and ask the Lead (`docs/TEAM_WORKFLOW.md` §6).

## 7. Data and secrets

- Contract products in `data/products/` are committed through **Git LFS** (D-027; `*.parquet` there is tracked by `.gitattributes`). NASA raw archives (`data/raw/`) and interim files (`data/interim/`) are never committed: they are far too large and are re-downloaded or regenerated. Small `SYNTHETIC` fixtures (<5 MB) are committed normally under `data/fixtures/`. Run `git lfs install` once per machine before cloning or pulling.
- Secrets go in `.env`, which is ignored. Document variable names in `.env.example`.
- If a secret is committed by mistake: tell the Lead immediately and **rotate the key**. Rewriting history alone is not enough.

## 8. Protection of `main`: policy vs settings

The no-direct-push rule is **documented policy plus an optional local guard**. GitHub branch protection is **not** configured (verified 2026-11-14) and collaborators can technically push. See `docs/TEAM_WORKFLOW.md` §10 and decision D-019.
