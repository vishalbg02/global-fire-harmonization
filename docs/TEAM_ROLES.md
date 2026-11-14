# Team Roles

There are three members. Handles are filled in by the Project Lead when collaborators are added.

| Member | Role | GitHub handle |
|---|---|---|
| Member 1 | Project Lead / CTO / Supervisor | `vishalbg02` |
| Member 2 | Data Engineering & Scientific Analysis | *TBD* |
| Member 3 | Application Development & UI | *TBD* |

## 1. Responsibility matrix (R = responsible, A = approves, C = consulted, I = informed)

| Area | M1 Lead | M2 Data/Science | M3 App/UI |
|---|---|---|---|
| **Task assignment** (tracker: owner, branch, status) | **A/R** | I | I |
| **Task prompt** for an assigned task (own Claude session) | Reviews in the draft PR | **R** (own tasks) | **R** (own tasks) |
| **PR review and approve / request changes / reject** | **A/R** (every PR) | — | — |
| Scope, priorities, cuts | **A/R** | C | C |
| Tech stack (D-008) | **A** | C | C |
| Data contract | **A** | **R** (producer) | **R** (consumer) |
| Data acquisition and processing | I | **R** | — |
| Calibration, uncertainty, verdict rules | **A** (method review) | **R** | I |
| Validation thresholds (pre-registration) | **A/R** (defines cases and windows) | **R** (implements) | I |
| Validation execution and write-up | **A** (review) | **R** | I |
| `harmonize_area()` function | I | **R** | C (calls it) |
| API endpoints | C | C | **R** (if D-015 is accepted) |
| Map, calendar, panels, export UI | C | C (wording of science) | **R** |
| Methods/validation page content | **A** | **R** (content) | **R** (rendering) |
| Merging PRs to `main` | **A/R** (only the Lead merges) | — | — |
| Demo video, project page, submission | **R** | C | C |
| Docs: decision log, progress, handoff | **R** | R (own areas) | R (own areas) |

## 2. Deliverables and acceptance criteria

### Member 1: Project Lead (supervises; not a primary implementer)

| ID | Deliverable | Due | Acceptance |
|---|---|---|---|
| L1 | Stack and contract approval recorded (D-008, D-009 draft) | H1 | Entries in `DECISION_LOG.md` |
| L2 | Validation case definitions: bounding boxes, months, quiet months for A2 (T-050) | H6 | Table in `VALIDATION_PLAN.md` |
| L3 | G1 lock: grid sizes, baseline, verdict thresholds, validation thresholds (T-051) | H8 | Logged as approved |
| L4 | Reviews R1–R4 (see the schedule) with written outcomes | H8, H14, H26, H31 | Notes in `PROGRESS_LOG.md` |
| L5 | Demo storyline, video with English subtitles, project page | H32 | Links working |
| L6 | Submission | H34 | Confirmed on the Space Apps site |

### Member 2: Data Engineering & Scientific Analysis (critical path)

| ID | Deliverable | Due | Acceptance |
|---|---|---|---|
| D1 | All zips downloaded; 2026 API pulled; MAP_KEY in `.env` only | H2 (pulls continue in the background) | File list and checksums recorded in `data/README.md` snapshot notes |
| D2 | `SYNTHETIC` fixtures for every contract product | H3 | Pass contract validation; committed under `data/fixtures/` (<5 MB) |
| D3 | Normalized detections (Parquet) with QA summary: row counts per sensor and year, filters applied, version-field finding | H6 | Counts recorded in `DATA_SOURCES.md` (replacing estimates) |
| D4 | `cell_month_witness` global, plus the raw-jump evidence plot | H8 (G1) | Lead review R1 |
| D5 | `calibration` with pooling, bootstrap uncertainty and holdout scores | H13 | Lead review R2 |
| D6 | `cell_month_harmonized`, `entity_month`, `metadata.json`; `harmonize_area()` importable | H22 | Products validate against the contract |
| D7 | `validation_results.json` with actual statuses; `VALIDATION_PLAN.md` actual-results table filled | H26 | Lead review R3 |
| D8 | Methodology document updated to the implemented method | H30 | Lead approval |

### Member 3: Application Development & UI

| ID | Deliverable | Due | Acceptance |
|---|---|---|---|
| A1 | Approved environment set up; app skeleton runs | H2 | Runs on two machines |
| A2 | Global map with country layer and cell layer (fixtures) | H6 | 60 fps-class interaction on a laptop [target, not measured] |
| A3 | Calendar + raw/harmonized toggle (fixtures) | H8 | Accessible colour ramps; legend |
| A4 | API serving fixtures for all endpoints in `ARCHITECTURE.md` | H10 | Responses validate against the contract |
| A5 | Country/continent/rectangle selection; evidence panel; witness chart | H18 | Works end-to-end on fixtures |
| A6 | Real-data integration; CSV export | H26 | Lead review R3 |
| A7 | Anomaly list; methods and validation page | H28 | Renders `validation_results.json` faithfully, including failures |
| A8 | Static fallback build; optional deploy | H32 | Preset views work without the API |

## 3. Dependencies and hand-offs

| From → To | What | When | Format |
|---|---|---|---|
| M1 → all | Approved stack and contract | H1 | `DECISION_LOG.md` |
| M2 → M3 | SYNTHETIC fixtures | H3 | `data/fixtures/` per the contract |
| M1 → M2 | Validation case windows | H6 | `VALIDATION_PLAN.md` |
| M2 → M1 | G1 evidence (raw-jump plot, QA counts) | H8 | PR + `PROGRESS_LOG.md` |
| M2 → M3 | `harmonize_area()` signature and stub | H10 | Python module + docstring |
| M2 → M3 | Real products | H22 | `data/products/` (not in Git; shared via a team drive or regenerated locally) |
| M2 → M3 | `validation_results.json` | H26 | Contract §6 |
| M3 → M1 | Demo-ready build | H28 | Tagged commit |

## 4. Ownership boundaries

| Owner | Owns | Must not modify without Lead approval |
|---|---|---|
| **M1 Lead** | Task assignment; `DECISION_LOG.md`; tracker statuses; `PROGRESS_LOG.md`; `HANDOFF.md`; `VALIDATION_PLAN.md` case definitions and thresholds; demo and submission | Teammates' implementation code (review only; request changes instead) |
| **M2 Data & Science** | The pipeline directory (name set when the stack is approved, D-008/T-0D); `data/` conventions and fixtures; `SCIENTIFIC_METHODOLOGY.md` implementation details; validation results | App and API directories; the data contract; the methodology's approved decisions |
| **M3 App & UI** | The app and API directories (API subject to D-015); UI text for reason codes (wording approved by M1) | Pipeline code; the data contract; scientific logic (the API **calls** `harmonize_area()`, it never reimplements it) |
| **Shared, Lead-gated** | `DATA_CONTRACT.md`, `ARCHITECTURE.md`, `TECH_STACK.md`, `TEAM_WORKFLOW.md`, `CLAUDE.md`, `CONTRIBUTING.md` | Everyone: change only through a Lead-approved PR |

- Integration issues between M2 and M3 go to the Lead, not to direct edits in each other's code.
- Each member's Claude session is bound by the same boundaries (`CLAUDE.md`).

## 5. Review and approval process

1. The Lead assigns a task in `TASK_TRACKER.md`.
2. The teammate's Claude session generates the task prompt (`TEAM_WORKFLOW.md` §4).
3. The teammate works on a task branch and opens a draft PR early.
4. The PR is submitted for review.
5. The Lead reviews **every** PR with the checklist in `CONTRIBUTING.md`. The outcome is **Approved**, **Changes requested** (fix in the same PR) or **Rejected** (the task is reconsidered).
6. **Only the Lead merges into `main`,** and personally authorizes each merge. No teammate and no AI session merges or approves.
7. Scientific, architectural, contract and stack changes need the Lead's explicit approval, logged in `DECISION_LOG.md`.
8. Disagreements: the owner proposes, the other member comments, and the Lead decides within 30 minutes or picks the documented default.

The full process is in [`TEAM_WORKFLOW.md`](TEAM_WORKFLOW.md).

## 5a. Individual Claude sessions

- Each member may use their own Claude account or session. Sessions share **no** memory, so the repository documents are the only shared context.
- A session must run the startup checklist (`CLAUDE.md`). It works only on the member's assigned task and never expands scope.

## 6. Note for the Lead

Member 2 carries the critical path (download → grid → calibrate → verdicts → validation). The schedule deliberately moves non-implementation work to the Lead: validation case definitions, G1 locks, demo, submission and documentation. If Member 2 falls behind at G1 or G2, the Lead triggers Fallback A or B rather than cutting validation.
