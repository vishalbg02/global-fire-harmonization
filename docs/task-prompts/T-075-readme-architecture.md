# Task prompt: T-075 Judge-facing README and architecture refresh

> Prepared for: Member 2 · Date: 2026-11-15 · Based on main (HEAD at branch creation)
> Source of truth: `docs/TASK_TRACKER.md` row T-075 (PR #74) and the Lead's audit of 2026-11-15: `README.md` and `docs/ARCHITECTURE.md` still say "no application code".

## 1. Project context
The README is the first thing a judge opens. It still describes the H0 state. The application, the API, the pipeline, the real products and the validation results now exist.

## 2. Task objective
A README that lets a newcomer understand the project, run the app from the README alone, and see the results including the failures; an ARCHITECTURE document that describes the system as built.

## 3. Assigned responsibility
T-075 / P0 · Owner: Member 2 · Reviewer and merger: Member 1 · Dependency: T-027 (merged). T-077 then follows the README on a fresh clone and fixes any step that does not work.

## 4. Relevant files and directories
- Modify: `README.md`, `docs/ARCHITECTURE.md`
- Read: `api/README.md`, `app/README.md`, `data/README.md`, `docs/TECH_STACK.md`, `docs/VALIDATION_PLAN.md` §4, `data/products/validation_results.json`, `data/products/metadata.json`, `docs/DECISION_LOG.md`, `docs/RISKS_AND_LIMITATIONS.md`
- Not touched: `docs/HANDOFF.md` and `docs/PROGRESS_LOG.md` (the Lead's T-082), code, products, the validation plan wording

## 5. Approved technologies
None added. Markdown and Mermaid only.

## 6. Architecture and data contract
No change to the system. ARCHITECTURE.md is updated to describe what was built; where it changed from the proposal, the section says so and cites the decision.

## 7. Inputs
The merged repository on `main`.

## 8. Expected outputs
A README with: what the project is and does not claim; what the app does; results with the failures and links; how to run it in a few commands (clone, LFS, Python environment, API, app, tests); data sources, limits and acknowledgement; a documentation map; the team. An ARCHITECTURE.md as built.

## 9. Implementation requirements
1. **Every number carries a label** (verified, estimate, assumption, hypothesis) and says where it comes from (a product, a file or a command). Counts of results are read from `data/products/validation_results.json`; nothing is invented.
2. **Failures stay visible:** the README states which validation tests failed and links to `docs/VALIDATION_PLAN.md` §4 and the results files. No softer wording than the Lead's decisions (D-029, D-030 not adopted, the D1 reading, S1).
3. **Commands are the ones that work:** each is run in T-077 on a fresh clone and corrected there.
4. The core principle stays (a hotspot is not a fire count or burned area) and so does the data acknowledgement.
5. No AI attribution anywhere (D-020).

## 10. Constraints: do not modify
Method, thresholds, products, the validation plan's wording, HANDOFF and PROGRESS_LOG, code.

## 11. Acceptance criteria
A newcomer can run the app from the README alone; every number is labelled and sourced; failures are visible.

## 12. Required tests
Not applicable (documentation). Links are checked with a script (relative links resolve to existing files); commands are verified in T-077.

## 13. Documentation updates
`README.md`, `docs/ARCHITECTURE.md`.

## 14. Git branch and PR instructions
Branch `docs/T-075-readme-architecture` from the latest `main`; first commit: this prompt; open a PR with the template; never merge; human identity (D-020).

## 15. Out-of-scope or blocking issues
Screenshots of the new UI wait for Member 3's UI PRs (T-070 to T-074); the README links to the demo materials when the Lead adds them.
