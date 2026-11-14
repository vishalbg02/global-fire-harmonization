# Decision Log

Approval status: **APPROVED** (by the Project Lead) · **PROPOSED** (awaiting approval) · **OPEN** (not yet proposed or decided) · **SUPERSEDED**.

| ID | Date | Decision | Status |
|---|---|---|---|
| D-001 | 2026-11-14 | Challenge: Harmonization of MODIS and VIIRS Hot Spots | APPROVED |
| D-002 | 2026-11-14 | Global scope (not selected regions) | APPROVED |
| D-003 | 2026-11-14 | Product direction: Many Witnesses + Witness Stand | APPROVED (implicitly, by proceeding to the global plan; Lead to confirm) |
| D-004 | 2026-11-14 | Historical data from FIRMS global yearly zips; 2026 from the area API | PROPOSED |
| D-005 | 2026-11-14 | Aqua as display scale; drift cutoff measured empirically: Aqua night excluded from 2024-05 (documented deviation from the registered day-only rule), Aqua day stays | **APPROVED** (2026-11-14) |
| D-006 | 2026-11-14 | Harmonized record starts 2002-07; Terra in the raw view only | PROPOSED |
| D-007 | 2026-11-14 | NOAA-21 excluded from the MVP | PROPOSED |
| D-008 | 2026-11-14 | Technology stack | **APPROVED** (2026-11-14, as recommended) |
| D-009 | 2026-11-14 | Regular lat/lon grid: analysis 0.5°, fine 0.05° (locked at G1 on the Aqua vs S-NPP 2012–2016 test) | APPROVED (2026-11-14) |
| D-010 | 2026-11-14 | Baseline 2003–2022 + Aqua-only sensitivity test | **APPROVED** (2026-11-14, D-028) |
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
| D-028 | 2026-11-14 | G1 lock (T-051): baseline, probabilities, verdict and minimum-data thresholds, reason-code rules; validation thresholds locked as written | **APPROVED** (2026-11-14) |
| D-027 | 2026-11-14 | Contract products in `data/products/` are committed through Git LFS; raw and interim data stay out of Git | **APPROVED** (2026-11-14) |
| D-026 | 2026-11-14 | Reason code `NOT_HARMONIZED` and raw-only products (contract 0.1.1) | **APPROVED** (2026-11-14) |
| D-025 | 2026-11-14 | Persistent night sources join the static mask; no local calibration for one-month bursts | **APPROVED** (2026-11-14) |
| D-024 | 2026-11-14 | Add `terra-draw-maplibre-gl-adapter` 1.5.0 to the frontend stack (drawing the custom rectangle on the MapLibre map, T-035) | **APPROVED** (2026-11-14) |
| D-030 | 2026-11-15 | v0.2 activity-dependent conversion (post-hoc, prompted by A1 and T-020b): adopted only by a pre-registered rule; v0.1 stays visible | **PROPOSED** (2026-11-15; adoption rule fixed before any v0.2 result) |
| D-029 | 2026-11-15 | Test A1: both paths use the shared Aqua-measured 2003-2022 baseline (amends D-028 for A1 only; adopted after seeing C1, whose official result stays INCONCLUSIVE) | **APPROVED** (2026-11-15) |

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
- **Result (T-012, PR #45):** the drift method was registered in `docs/task-prompts/T-012-holdout-drift.md` before any result: a change-point test on the global **day** series of S-NPP, drift called only if the slope interval excludes 0 and BIC prefers the break. It **did not detect drift** (onset 2025-06 at the edge of the range, slope -5.4% per year, flat model better by 6.1 BIC). It **missed a drift visible only at night**: global night is detected independently in both witnesses (S-NPP onset 2024-05, interval 2022-10 to 2025-04, -12.0% per year, delta BIC +28.9; NOAA-20 onset 2024-09, interval 2024-03 to 2025-02, -19.0% per year, delta BIC +50.7).
- **Approved decision (the Lead, 2026-11-14), a documented deviation from the registered rule:** **Aqua night is excluded from the combination from 2024-05 on; Aqua day stays** (no day cutoff, as the registered rule says). The earlier of the two night onsets is used, as the conservative choice. The affected months carry `AQUA_DRIFT_ERA`. Implemented as the module default `AQUA_FROM = {"D": None, "N": (2024, 5)}` in `pipeline/harmonize.py`; one method for all months (day and night combined separately and added), chosen by the Lead's seam rule (PR #45: the totals method differs from it by 0.35% at the median but 28% at the 95th percentile, against limits of 1% and 5%).
- **Limits:** the cutoff was chosen after seeing the results (the registered primary series did not give it); the cause (Aqua, processing or VIIRS) is open; the choice of 2024-05 rests on the earlier of two overlapping onset intervals.
- **Status:** **APPROVED** by the Lead, 2026-11-14.

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
- **Status:** **APPROVED** 2026-11-14, as specified in D-028 (G1 lock).

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

### D-027: Contract products through Git LFS
- **Context:** real products (about 180 MB for `cell_month_witness.parquet` alone) were shared outside Git (WhatsApp or Drive) with checksums. That is error-prone, and GitHub rejects normal files over 100 MB.
- **Decision:** commit the contract products in `data/products/` through **Git LFS**. `.gitattributes` tracks `data/products/**/*.parquet`; small JSON products are normal Git files. Members run `git lfs install` once per machine.
- **Not changed:** NASA raw archives (`data/raw/`, about 9.7 GB) and interim files (`data/interim/`, about 6.3 GB) are never committed. They are reproducible from FIRMS and the pipeline, and are too large for the LFS quota.
- **Cost:** every committed version stays in LFS history and counts against the account's LFS storage and bandwidth quota, so products are committed only when they change.
- **Status:** **APPROVED** by the Lead, 2026-11-14 (replaces the earlier "never commit products" rule).

### D-028: G1 lock (T-051): baseline, verdicts, data thresholds and validation thresholds **[APPROVED 2026-11-14]**
Fixed **before** any baseline, verdict or validation result exists (pre-registration). After approval, a change needs a new entry with its reason, and the original stays visible.

**1. Baseline (closes D-010).**
- Same calendar month, years **2003–2022** (20 years), from the harmonized estimates of `harmonize_area()` with the approved method (φ, κ, shared ratio errors, single day/night combination, D-005). 2003–2011 are Aqua-only; the D-005 cutoff does not touch these years.
- Percentiles **p25, p50 and p75**: empirical, linear interpolation between order statistics, over the baseline years that have an estimate.
- Sensitivity (test S1): an Aqua-measured baseline (2003–2021).
- Limitation kept: the uncertainty of the percentiles is not propagated in v0.1.

**2. Probabilities.** The estimate is treated as Normal(estimate, sd) truncated at 0. `p_above = P(X > p75)`, `p_below = P(X < p25)`, `p_within = 1 − p_above − p_below`.

**3. Verdicts, applied in this order.**
| Step | Condition | Verdict | Reason codes |
|---|---|---|---|
| 1 | No estimate (no witness with a complete month) | `CANNOT_DETERMINE` | `OUTAGE` |
| 2 | Fewer than **15 of the 20** baseline years have an estimate | `CANNOT_DETERMINE` | `INSUFFICIENT_BASELINE` |
| 3 | Estimate = 0 **and** baseline p75 ≤ **1** cell-day | `NO_DETECTED_ACTIVITY` | — (never "below normal") |
| 4 | Baseline p50 < **5** Aqua-equivalent cell-days (too little normal activity to judge) | `CANNOT_DETERMINE` | `INSUFFICIENT_BASELINE` |
| 5 | `p_above ≥ 0.8` | `ABOVE_NORMAL` | |
| 6 | `p_below ≥ 0.8` | `BELOW_NORMAL` | |
| 7 | `p_within ≥ 0.8` | `WITHIN_NORMAL` | |
| 8 | Otherwise | `CANNOT_DETERMINE` | `WIDE_INTERVAL` |

The threshold 5 matches the D-009 evidence ("Aqua ≥ 5 cell-days"); 0.8 is the method's proposed level (SCIENTIFIC_METHODOLOGY §4.6).

**4. Caveat codes** (added to any verdict; they never change it):
- `PROVISIONAL_NRT`: `data_level` is `NRT` or `MIXED`.
- `SINGLE_WITNESS`, `WITNESS_DISAGREEMENT` (S > 2), `AQUA_DRIFT_ERA` (D-005): as already produced by T-013.
- `POOLED_CALIBRATION`: more than 50% of the area's converted cell-days use `REGION` or `GLOBAL` ratios.
- `DIURNAL_CAVEAT`: India and the cells in 29.5–32.5 N, 73.8–77.5 E (Punjab and Haryana), October–November, from 2020 (documented burning-time shift).
- `INSUFFICIENT_OVERLAP`: reserved, not used in v0.1 (pooling covers thin overlap).

**5. Levels.** Verdicts for cells, countries, continents and the world, all from `harmonize_area()`. The share of land cells with a determinable verdict is reported (test D2).

**6. Validation thresholds.** Locked exactly as written in `docs/VALIDATION_PLAN.md` §3 (A1, A2, B1, B2, B3, C1, D1, D2, E1, CTRL, S1). Cases and windows: T-050 in `docs/VALIDATION_PLAN.md` §2.

- **Status:** **APPROVED** by the Lead, 2026-11-14 (G1 lock). D-010 is closed by this entry.

**Amendment A (T-014, PR #52), approved by the Lead 2026-11-15: step 3 also requires no detection by any witness.** `NO_DETECTED_ACTIVITY` is given only when the estimate is 0, the baseline p75 is at most 1 cell-day **and the raw combined cell-days are 0** (any witness, Terra included). If any satellite saw something, the product does not say "nothing detected": such a row goes on to step 4 and gets `INSUFFICIENT_BASELINE`. Reason: the contract checker (`contract_check.py`) forbids `NO_DETECTED_ACTIVITY` where detections are present; the checker is kept as it is. Rows moved by this amendment in the first run without it: **216,103 cell-months** (2.0% of the `NO_DETECTED_ACTIVITY` rows), **545 country-months** and **3 continent-months**. No threshold of D-028 changed.

### D-029: Test A1 uses the shared Aqua-measured 2003-2022 baseline for both paths (amends D-028 for A1 only) **[APPROVED 2026-11-15]**
- **Context:** A1 (`docs/VALIDATION_PLAN.md` §3) compares `pct_of_normal` from Aqua alone with `pct_of_normal` from converted S-NPP alone. D-028 builds a baseline from a path's own estimates and gives no baseline when fewer than 15 of the 20 years (2003-2022) have an estimate. S-NPP starts in 2012, so the S-NPP-only path has at most 11 baseline years and no baseline; case C1 (Indonesia, Sep-Oct 2015) was therefore INCONCLUSIVE as pre-registered (T-020, `docs/validation/T-020-results.md`).
- **Decision:** for test A1, **both paths use the same baseline: the Aqua-measured 2003-2022 baseline** (same calendar month, empirical p25/p50/p75 over the years with an Aqua-only estimate, minimum 15 years and median at least 5 cell-days as in D-028). The paths then differ only in the numerator (the Aqua-only estimate against the converted S-NPP-only estimate). Reason: the product compares every month against one 2003-2022 normal; an S-NPP-only normal built from 2012-2022 covers a different period, so its percentages are not comparable to Aqua's.
- **Timing, stated plainly:** this amendment was adopted **after C1 had been run and its three readings seen** (D-028 as written: INCONCLUSIVE; shared Aqua baseline: PASS; S-NPP own 2012-2022 baseline with a 10-year minimum: FAIL). It is applied **before** C2 to C6 are run. **C1's official result stays INCONCLUSIVE, as pre-registered**; its other two readings are published beside it and are not the official result. C1 counts as INCONCLUSIVE, not PASS, in the family result.
- **Unchanged:** the A1 criterion (same direction above or below normal; peak month within ±1; 90% intervals overlap), the family pass (at least 5 of 6 clean-overlap cases C1-C6), all other thresholds, and the baseline of every other test and of the product.
- **Limit kept:** both paths now share one baseline, so A1 tests the numerators only; the baseline is itself built from Aqua, and the baseline's uncertainty is not propagated (D-028).
- **Status:** **APPROVED** by the Lead, 2026-11-15.

### D-030: v0.2 activity-dependent conversion, adopted only by a pre-registered rule **[PROPOSED 2026-11-15]**
- **Context:** A1 failed for method 0.1.0 (0 of 6 cases, D-029). T-020b (`docs/validation/T-020b-saturation.md`) confirmed by a rule fixed in advance that the Aqua/VIIRS ratio rises with activity: a ratio fitted mostly on typical months under-converts extreme months, the direction of the A1 failure. The Lead asked for a time-boxed v0.2 (PR #58, decision by 10:00 IST on 2026-11-15).
- **Proposal (T-020c):** `ratio_v02 = ratio_v01(stratum, witness, day/night, season) x f(witness, day/night, activity bin)`, with one global factor per witness, day/night and bin fitted on the **fit periods only** (S-NPP 2012-01 to 2016-12, NOAA-20 2018-04 to 2021-12). Activity is the converted activity of the witness's own counts per analysis cell and month, in the eight bins of T-020b. `f = sum(Aqua) / sum(ratio_v01 x witness)` over the stratum-months of the bin; bins with fewer than 50 units take the nearest bin with 50 or more. The factor error is a shared, fully correlated error per bin. Everything else is as v0.1, and phi and kappa are re-estimated the same way on the fit periods. Design details: `docs/task-prompts/T-020c-v02-conversion.md` section 9.
- **Adoption rule (fixed by the Lead on PR #58, recorded before any v0.2 result exists).** Adopt v0.2 **only if all three hold:**
  1. holdout (T-012, 2017-2021) median absolute log error is no worse than v0.1 for regions **and** countries (day+night total);
  2. D1 pooled 90% coverage stays within 80 to 97%;
  3. the A1 gap (S-NPP-only over Aqua-only in the peak windows) gets smaller in at least 3 of the 4 failed cases C3 to C6.
  If it is not ready by 10:00 IST on 2026-11-15, or any condition fails, **v0.1 stays** and the A1 FAIL stays documented as a limitation (with the saturation finding in `docs/RISKS_AND_LIMITATIONS.md`).
- **Labelling:** a **post-hoc improvement prompted by A1**. A1 stays **FAIL for v0.1** permanently. The v0.2 A1 numbers are reported as not independent (the cases motivated the change). v0.1 and v0.2 results are shown side by side.
- **Safety:** v0.2 is built outside `data/products/` (`data/interim/v02/`); no product changes until this decision is approved. Approval of D-030 is needed before any v0.2 product, even if the rule is met.
- **Limits kept:** full pooling of `f` across strata at the bin level; errors of different bins and the stratum-ratio errors treated as independent; saturation as the mechanism is a hypothesis (T-020b).
- **Status:** **PROPOSED**; the Lead decides.
