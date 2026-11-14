# Contributing

This is a three-person hackathon team. The rules are kept light, and they are followed.

## Branches

- `main`: stable, demo-ready work only. **No direct pushes.** Only the Project Lead merges into `main`.
- Feature branches: `<area>/<task-id>-<short-name>`, for example:
  - `data/T-003-normalize`
  - `science/T-011-calibration`
  - `app/T-031-global-map`
  - `docs/T-051-g1-lock`
- Keep branches short-lived (a few hours). Rebase on, or merge from, `main` before opening a PR.

> GitHub Free does not offer branch protection on private repositories. "No direct pushes to `main`" is therefore enforced by this agreement and by review, not by settings.

## Commits

Use Conventional Commits, and reference the task ID:

```
feat(app): render analysis-cell layer for selected month (T-031)
fix(science): exclude outage months from baseline percentiles (T-014)
docs: lock G1 thresholds in VALIDATION_PLAN (T-051)
data: add SYNTHETIC fixtures for contract v0.1.0 (T-010)
```

Types: `feat`, `fix`, `docs`, `test`, `data`, `chore`, `refactor`.

## Pull requests

1. Open a PR from your feature branch into `main`. Title: `T-0XX: <what>`.
2. The description covers what changed, why, how it was tested, which docs were updated, and any contract or method impact.
3. Update docs in the **same PR**: `TASK_TRACKER.md`, plus `ARCHITECTURE.md`, `DATA_CONTRACT.md`, `SCIENTIFIC_METHODOLOGY.md`, `VALIDATION_PLAN.md` or `DECISION_LOG.md` as relevant.
4. Request the Project Lead's review. **Do not merge your own PR.** AI assistants never merge or approve on the Lead's behalf.
5. Small PRs are reviewed faster. Aim for under about 400 changed lines, excluding fixtures.

## Project Lead review checklist

- [ ] Does the implementation meet the task's acceptance criteria in `TASK_TRACKER.md`?
- [ ] Is the scientific interpretation correct (hotspots ≠ fires; no unsupported claims; uncertainty handled)?
- [ ] Are data assumptions documented (filters, thresholds, units)?
- [ ] Are edge cases handled (nulls, outages, zero baselines, no detections, provisional months)?
- [ ] Are tests present and passing (science on synthetic data with known answers; contract validation)?
- [ ] Does it integrate with the other workstream (conforms to `DATA_CONTRACT.md`)?
- [ ] Are documentation files updated in the same PR?
- [ ] Are there no secrets, `.env` files, credentials or large data files (anything over ~5 MB, raw/processed data)?
- [ ] Does it avoid regressions (existing views and tests still work)?
- [ ] For results shown to users: are the numbers traceable to products, and are synthetic fixtures clearly excluded?

## Data and secrets

- NASA archives and generated products live under `data/` and are git-ignored. See `data/README.md`.
- Only small `SYNTHETIC` fixtures (<5 MB total) may be committed, under `data/fixtures/`.
- Secrets go in `.env`, which is ignored. Document required variables in `.env.example`.
- If a secret is committed by mistake: tell the Lead immediately and rotate the key. Rewriting history alone is not enough.

## Resolving conflicts

1. The owner proposes and the other member comments.
2. The Lead decides, then logs it in `DECISION_LOG.md`.
3. Contract changes need Lead approval and a `contract_version` bump before any code change.
