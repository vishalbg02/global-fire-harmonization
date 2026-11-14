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
| D-012 | 2026-11-14 | Git workflow: feature branches, PRs, Lead-only merges | PROPOSED |
| D-013 | 2026-11-14 | Demo is local-first plus a recorded video; deployment optional | PROPOSED |
| D-014 | — | Repo visibility for judges at submission | OPEN |
| D-015 | — | API owner: Member 3 (recommended if Python-capable) or Member 2 | OPEN |
| D-016 | 2026-11-14 | Data contract v0.1.0 | PROPOSED |

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
- **Status:** PROPOSED.

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
