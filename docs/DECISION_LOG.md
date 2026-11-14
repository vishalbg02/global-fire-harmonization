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
| D-008 | 2026-11-14 | Technology stack | **APPROVED** (2026-11-14, as recommended) |
| D-009 | 2026-11-14 | Regular lat/lon grid: analysis 0.5°, fine 0.05° (locked at G1 on the Aqua vs S-NPP 2012–2016 test) | APPROVED (2026-11-14) |
| D-010 | 2026-11-14 | Baseline 2003–2022 + Aqua-only sensitivity test | PROPOSED |
| D-011 | 2026-11-14 | Private GitHub repo; collaborators added by the Lead only | APPROVED |
| D-012 | 2026-11-14 | Git workflow: feature branches, PRs, Lead-only merges | SUPERSEDED by D-017 |
| D-013 | 2026-11-14 | Demo is local-first plus a recorded video; deployment optional | PROPOSED |
| D-014 | — | Repo visibility for judges at submission | OPEN |
| D-015 | 2026-11-14 | API owner: Member 3 | **APPROVED** |
| D-023 | 2026-11-14 | Directory layout: `pipeline/` (Member 2), `api/` and `app/` (Member 3), `data/`, `docs/` (T-0D) | **APPROVED** |
| D-016 | 2026-11-14 | Data contract v0.1.0 | **APPROVED** (2026-11-14, as written) |
| D-017 | 2026-11-14 | Team workflow: Lead assigns tasks; individual Claude sessions generate task prompts; one branch + PR per task; Lead reviews every PR and alone merges | APPROVED (Lead's instruction); **in effect** since PR #2 merged (2026-11-14) |
| D-018 | 2026-11-14 | Lead bookkeeping commits allowed directly on `main` (tracker, decision log, progress log, handoff only) | PROPOSED |
| D-019 | — | Technical protection of `main` (GitHub Pro branch protection vs policy + local guard) | OPEN |
| D-022 | 2026-11-14 | Contract additions from the workstream prompts (cell_id, cell bounds, entity IDs, PRODUCTS_DIR, path rule); envelope and error format not adopted → contract 0.1.1 | **APPROVED** (2026-11-14) |
| D-020 | 2026-11-14 | No AI names or AI-generated attribution in commits, PRs, branch names, code comments, credits or metadata; human Git identity only | APPROVED (Lead's instruction) |
| D-021 | 2026-11-14 | Rewrite the 4 bootstrap commits on `main` to remove AI trailers | APPROVED and DONE (force-pushed 2026-11-14) |
| D-026 | 2026-11-14 | Reason code `NOT_HARMONIZED` and raw-only products (contract 0.1.1) | **APPROVED** (2026-11-14) |
| D-025 | 2026-11-14 | Persistent night sources join the static mask; no local calibration for one-month bursts | **APPROVED** (2026-11-14) |
| D-024 | 2026-11-14 | Add `terra-draw-maplibre-gl-adapter` 1.5.0 to the frontend stack (drawing the custom rectangle on the MapLibre map, T-035) | **APPROVED** (2026-11-14) |

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
- **Decision:** the recommended stack in `TECH_STACK.md` §2, without amendments. The final table is in `TECH_STACK.md` §7.
- **Status:** **APPROVED** by the Project Lead, 2026-11-14 12:26 IST. This time is **H0** of the 36-hour schedule.

### D-009: Grid
- **Decision:** a regular lat/lon grid with an **analysis grid of 0.5°** and a **fine cell-day grid of 0.05°**. A fine cell belongs to the analysis cell that holds its centre.
- **How it was chosen (pre-registered rule):** best Aqua vs S-NPP agreement on 2012–2016 (SP data, approved filters and static mask, day and night combined), measured before any validation. Member 2's test (PR #27), measured:

  | Fine | Analysis | Spearman | Both > 0 | Aqua ≥ 5 cell-days |
  |---|---|---|---|---|
  | 0.05° | 0.25° | 0.672 | 13.3% | 4.5% |
  | **0.05°** | **0.5°** | **0.739** | **21.0%** | **8.8%** |
  | 0.1° | 0.25° | 0.664 | 13.2% | 4.1% |
  | 0.1° | 0.5° | 0.733 | 21.0% | 8.4% |

- **Known consequences:** Aqua night activity is thin (Spearman 0.41–0.51), so night strata will rely on pooling. Only about 9% of cell-months reach Aqua ≥ 5 cell-days, so cell-level verdicts will often be `CANNOT_DETERMINE`; country and continent are the main verdict levels. The 0.05° fine cell is close to a MODIS edge pixel at high latitudes; the 0.1° alternative scored slightly lower (0.733).
- **Status:** APPROVED by the Lead, 2026-11-14 (G1).

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
- **Decision:** Member 3 builds the thin API, which calls Member 2's `harmonize_area()`.
- **Status:** **APPROVED** by the Lead, 2026-11-14.

### D-023: Directory layout (T-0D)
- **Decision:** `pipeline/` holds Member 2's data and science code. `api/` holds the API (Member 3). `app/` holds the web app (Member 3). `data/` and `docs/` are unchanged. Each member writes only in their own folders.
- **Status:** **APPROVED** by the Lead, 2026-11-14.

### D-016: Data contract v0.1.0
- **Decision:** `DATA_CONTRACT.md` v0.1.0 **as written**. Its "Open items" (grid sizes, season definition, final `cell_id` format) are still decided at G1.
- **Not included:** the [PROPOSED ADDITION] items in the workstream prompts (see D-022).
- **Status:** **APPROVED** by the Project Lead, 2026-11-14.

### D-022: Contract additions from the workstream prompts
- **Items** (from `docs/prompts/*` §S):
  - `cell_id` format `g{RRR}_r{row}_c{col}` (rows from the south, columns from −180)
  - cell bounds lower-inclusive
  - entity ID scheme
  - API response envelope and error format
  - `PRODUCTS_DIR` environment variable
  - product path rule (a single file or a year-partitioned directory)
- **Effect if approved:** add them to `DATA_CONTRACT.md` and bump to `0.1.1`.
- **Status:** PROPOSED. Awaiting the Lead.

- **Decision (2026-11-14):** approved, except the API response envelope and error format, which are not adopted (bare payloads and FastAPI's default errors, per the Lead's T-034 answer). `PRODUCTS_DIR` defaults to `data/products`. Entity IDs include `AN` (it has data) and Kosovo `XKX`.
- **Status:** **APPROVED** by the Lead, 2026-11-14 → `DATA_CONTRACT.md` 0.1.1.

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

### D-024: Add terra-draw-maplibre-gl-adapter 1.5.0 to the frontend stack
- **Context:** the approved stack (D-008) names `terra-draw` for drawing the custom-area rectangle. `terra-draw` does not draw on a map by itself: it needs a separate adapter for the mapping library, and for MapLibre that is `terra-draw-maplibre-gl-adapter`. It was found while preparing T-035 and raised on PR #30.
- **Decision:** add `terra-draw-maplibre-gl-adapter`, pinned exactly to **1.5.0** (MIT licence; the official companion of `terra-draw`), to the frontend stack. `npm audit` must stay at 0 vulnerabilities.
- **Effect:** `docs/TECH_STACK.md` §7 gains one row. No other part of the stack changes.
- **Status:** **APPROVED** by the Lead, 2026-11-14.

### D-025: Persistent night sources join the static mask; no local calibration for one-month bursts
- **Context:** on PR #36 (T-011) the extreme night calibration ratios were traced to unlabelled gas flares and industrial heat (Permian, Bakken, Eagle Ford and others) and to volcanoes (Yasur, Fagradalsfjall). Evidence and numbers: `docs/DATA_SOURCES.md`, section "Extreme ratios: causes".
- **Decision 1: the static mask gains persistent night sources.** A 0.05 degree fine cell is masked if its kept VIIRS night detections (S-NPP or NOAA-20; SP, type 0, confidence n or h, not already in the T-005 mask), over 2012 to 2025:
  - light it on at least 1% of nights;
  - in at least 10 of the 12 calendar months;
  - with at least half of those nights outside its 3 busiest calendar months;
  - and its kept VIIRS day detections fall on at most 0.5 times as many days as its nights. This fourth condition was added after the Lead's review: a flare burns around the clock, a vegetation fire mostly in the afternoon. It keeps the Chiquitano dry forest (Bolivia) out of the mask.
  The cells are added to the approved T-005 mask, which applies to every witness, both day and night, and all years. Built by `pipeline/night_mask.py`; `pipeline/gridding.py` uses the combined mask by default, and `--mask` remains for comparisons.
- **Decision 2: one-off events get no local weight.** In calibration, a stratum x witness x day/night x season whose single largest overlap month holds more than 50% of its overlap cell-days (Aqua or witness) takes its region's estimate. This is a general rule instead of a volcano list (`MAX_MONTH_SHARE` in `pipeline/calibration.py`).
- **Not changed:** the low night ratios in savanna and agricultural fire regions are accepted as a hypothesis (real regional differences: VIIRS sees more small night fires than MODIS). T-012 and validation test E1 by region are to check it.
- **Limitations accepted:** the 8 Bolivian cells still flagged (cause open) and the Fagradalsfjall NOAA-20 JJA night ratio (a season-year test would move about 23% of `LOCAL` rows). Both are recorded in `docs/RISKS_AND_LIMITATIONS.md` (S12 to S15).
- **Status:** **APPROVED by the Lead 2026-11-14** (PR #36, after the re-run).

### D-026: Reason code `NOT_HARMONIZED` and raw-only products
- **Context:** Member 3 needed real data before harmonization exists (T-039 phase 1). Member 2 published raw-only `cell_month_harmonized` and `entity_month` (T-014a, PR #40).
- **Decision:** add the reason code `NOT_HARMONIZED` (contract 0.1.1). A raw-only row fills only the raw fields; every harmonized field is `null`, `witnesses_used = []`, `verdict = CANNOT_DETERMINE`, `reason_codes = ["NOT_HARMONIZED"]`, and `method_version` ends in `-raw-only`. T-014 replaces these products.
- **User-facing text:** "Harmonized values aren't computed yet; this shows raw satellite data only."
- **Status:** **APPROVED** by the Lead, 2026-11-14.
