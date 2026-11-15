# Global Fire Harmonization (working name: *Many Witnesses*)

NASA Space Apps Challenge 2026 project for the challenge
**[Harmonization of MODIS and VIIRS Hot Spots](https://www.spaceappschallenge.org/2026/challenges/modis-and-viirs-hot-spots/)**.

> **Status:** built and validated for method **0.1.0**. The pipeline, the data products, the API and the web app exist and run locally; the validation suite ran and **some tests failed. The failures are published below, in the app and in the documents.** See [`docs/HANDOFF.md`](docs/HANDOFF.md) for the Lead's current state notes.

## What it does

Satellites detect fire hotspots, but each one sees fire differently: MODIS (1 km) and VIIRS (375 m) differ in sensitivity, satellites join and leave, Aqua's orbit has drifted, and there are data gaps. Raw hotspot counts therefore cannot be compared across years. This project turns NASA FIRMS hotspots into **one harmonized monthly record of fire activity, July 2002 to the latest month**, for any 0.5-degree map cell, country, continent, the world or a custom area, and says when the evidence is too weak.

- **Three "witnesses"** are combined: Aqua MODIS (the reference scale), S-NPP VIIRS and NOAA-20 VIIRS (Terra MODIS is shown in the raw view only).
- **Every area and month gets a verdict:** above normal, within normal, below normal, cannot determine, or no detected activity. "Normal" is the same calendar month in 2003 to 2022. Each verdict comes with a 90% interval, the probabilities behind it and an **evidence panel** that names the satellites used and the caveats.
- **A published validation suite** (the *Witness Stand*, [`docs/VALIDATION_PLAN.md`](docs/VALIDATION_PLAN.md)) sits behind the verdicts, and the app's Methods and validation page shows every result, failures included.
- **The challenge's asks** are covered: a burning-activity calendar (years by months) joining MODIS history with VIIRS continuity, comparison against the historical median ("% of normal"), and CSV export.

## Core principle

A hotspot is a satellite pixel flagged as containing fire. It is **not** a fire count, a perimeter or burned area. No satellite tells the whole truth, so each one is weighed as a witness according to what it could actually see, and the tool says **"cannot determine"** when the evidence is insufficient. Passing the tests shows the method behaves correctly *where tested*; it does not establish global accuracy.

## Results at a glance

Method 0.1.0, run 2026-11-14 and 2026-11-15. Source of every number: [`data/products/validation_results.json`](data/products/validation_results.json) (38 entries: **18 PASS, 18 FAIL, 2 INCONCLUSIVE, 0 NOT_RUN**, counted from the file) and the table in [`docs/VALIDATION_PLAN.md`](docs/VALIDATION_PLAN.md) §4, with a report per task in [`docs/validation/`](docs/validation/). Thresholds were fixed before results were seen and were not changed afterwards.

| Test | Result | What it means |
|---|---|---|
| A1 two independent paths, 6 big fire events | **FAIL** (0 of 6 pass; 2 inconclusive, 4 fail) | Converted S-NPP reads 58% to 80% of Aqua in the peak months of the four decided events, in the same direction and the same peak month. A diagnostic found the Aqua/VIIRS ratio rises with activity ([`T-020b`](docs/validation/T-020b-saturation.md)); a v0.2 fix was built and **not adopted** because it did not meet the pre-registered rule ([`T-020c`](docs/validation/T-020c-v02.md), D-030). |
| A2 same fire in two eras | **FAIL** (0 of 3) | The raw satellite mismatch is visible, but harmonized S-NPP stays below harmonized Aqua. |
| B1 steps at satellite changes | PASS | The raw record steps by 2.6 to 4.3 times at 2012; the harmonized record is within 10% in 14 of 14 regions (13 of 14 at 2018). |
| B2 planted jump | **FAIL** | Detection 84.5% (needs 90%) and 25% false flags (needs under 5%). The disagreement flag is not a reliable change detector. |
| B3 drift and outages | PASS | Drift is visible at night only (onset 2024-05 S-NPP, 2024-09 NOAA-20); every outage month is "cannot determine". |
| C1 cross-satellite agreement | PASS | 97.6% of 630 fire-region-months agree within the 90% intervals. |
| CTRL savanna control | **FAIL** | 3 spurious above/below verdicts at the satellite-change dates. |
| D1 interval coverage | PASS pooled (0.818); **per-region and night readings FAIL** | The 90% intervals cover 82% of held-out values overall, but only 7 of 14 regions are inside 80% to 97%, and night coverage is 0.750. |
| D2 gaps | PASS | Missing data never produce a verdict. |
| E1 leave one region out | PASS (14 of 14), a weak bar | The unseen-region interval covers only 10% to 80%; intervals are not valid for regions without their own calibration data. |
| S1 sensitivity | **FAIL** (baseline half); confidence-filter half PASS | One of 13 peak-window verdicts changes with an Aqua-measured baseline. |

What this means for use: the record is reliable **where tested**, extreme months are likely **under-converted** for the VIIRS witnesses (T-020b; the mechanism, saturation, is a hypothesis), and cell-level verdicts are often "cannot determine" (country, continent and world views are the primary readings). Full list of failures with the claim narrowed for each: [`docs/VALIDATION_PLAN.md`](docs/VALIDATION_PLAN.md) §5 and [`docs/RISKS_AND_LIMITATIONS.md`](docs/RISKS_AND_LIMITATIONS.md).

### Featured cases (stored values; queries in `docs/validation/T-079-featured-stories.md` once PR T-079 is merged)

Verified against `data/products/entity_month.parquet`: Indonesia 2015-09 reads above normal at 265% of normal; Australia 2019-12 at 328%; Canada 2023-08 at 1024%; Brazil 2019-08 reads **within** normal (114%); the world in 2026-10 reads "cannot determine".

## Run it

Prerequisites: **Git** with **Git LFS** (the data products are in LFS), **Python 3.12 to 3.14**, **Node.js 22.12+ or 24 LTS** with npm. About 1 GB of disk for the products. You do **not** need the NASA raw archive or a MAP_KEY to run the app (they are only needed to rebuild the products, see below).

```bash
git clone https://github.com/vishalbg02/global-fire-harmonization.git
cd global-fire-harmonization
git lfs install
git lfs pull                                   # downloads data/products/*.parquet (about 600 MB)
```

**1. The API** (reads `data/products/`; start it from the repository root, because the default products folder is relative to the folder you start from):

```bash
python -m venv .venv
.venv/bin/pip install -r api/requirements.txt            # Windows PowerShell: .venv\Scripts\pip install -r api\requirements.txt
.venv/bin/uvicorn fire_api.main:app --app-dir api --port 8000      # Windows: .venv\Scripts\uvicorn fire_api.main:app --app-dir api --port 8000
```

Check it: `http://127.0.0.1:8000/api/meta` (versions, latest month) and the interactive docs at `http://127.0.0.1:8000/docs`.

**2. The web app** (in a second terminal; Vite proxies `/api` to port 8000):

```bash
cd app
npm ci
npm run dev                                    # open the address Vite prints, use "localhost"
```

**3. Tests and checks:**

```bash
.venv/bin/python -m pytest pipeline/tests api/tests -q   # science and API tests (Windows: .venv\Scripts\python)
.venv/bin/python -m ruff check pipeline api              # lint
.venv/bin/python pipeline/contract_check.py data/products --real   # contract check of the real products (loads the 420 MB table into memory: see below)
cd app && npm test && npm run typecheck && npm run lint
```

The full contract check needs a lot of free memory (in the T-077 run it stopped with a memory error on a 15.6 GB machine with 7.2 GB free). To check the small tables only (about 3 seconds):

```bash
.venv/bin/python -c "import sys; sys.path.insert(0, 'pipeline'); from pathlib import Path; import contract_check as c; print(c.check_dir(Path('data/products'), real=True, only=('entity_month', 'cells', 'calibration')))"   # prints [] when conforming
```

**No API at hand?** The app can run from a static copy of the preset views (offline mode, `app/README.md`). The API has a `SYNTHETIC` fixture mode for development (`PRODUCTS_DIR=data/fixtures/v0.1.0`); the app then shows a "SYNTHETIC DATA" banner. Never present fixture data as a result.

### Rebuilding the products (optional, long)

The products in `data/products/` are final for method 0.1.0 and are committed. Rebuilding them needs a free NASA FIRMS MAP_KEY (copy `.env.example` to `.env`, never commit it), about 60 GB of disk and many hours; the steps, scripts and checksums are in [`data/README.md`](data/README.md) and [`docs/DATA_SOURCES.md`](docs/DATA_SOURCES.md).

## How it works

```
NASA FIRMS (zips 2000-2025, area API 2026)
  -> pipeline/   acquire -> normalize -> grid (cell-day -> cell-month) -> calibrate (pooled ratios)
                 -> harmonize and combine -> baseline, probabilities, verdicts -> validation
  -> data/products/   Parquet + JSON, the data contract (docs/DATA_CONTRACT.md, Git LFS)
  -> api/        read-only FastAPI + DuckDB; custom areas through the same harmonize_area()
  -> app/        React + Vite: map, calendar, evidence panel, anomaly list, methods page, CSV
```

One function, `harmonize_area()`, does the science for every area (preset and custom), because conversion errors are shared by all cells of a calibration stratum and per-cell intervals must not be summed. Details: [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) (as built) and [`docs/SCIENTIFIC_METHODOLOGY.md`](docs/SCIENTIFIC_METHODOLOGY.md).

## Data sources and limits

- **Data:** NASA FIRMS active-fire archives (MODIS and VIIRS 375 m, standard and near-real-time). Snapshot of 2026-11-14; the latest four months (2026-08 to 2026-11) are **provisional** (near-real-time) and can change. Product row counts and dates: `data/products/metadata.json`.
- **Not in the record:** fire counts, perimeters, burned area, fire radiative power trends, causes. Terra MODIS enters the raw view only. Aqua night data are excluded from 2024-05 (orbit drift, D-005).
- **Known limitations** (permanent, shown in the app): [`docs/RISKS_AND_LIMITATIONS.md`](docs/RISKS_AND_LIMITATIONS.md). Notably: cells with a very small historical normal read "cannot determine" even in extreme months (D-031); intervals are too narrow at night and in about half of the regions; regional burning-time shifts (for example Punjab) carry a caveat and are never read as a decline.

## Documentation map

| Document | Purpose |
|---|---|
| [`docs/HANDOFF.md`](docs/HANDOFF.md) | Current state for anyone resuming |
| [`docs/VALIDATION_PLAN.md`](docs/VALIDATION_PLAN.md) and [`docs/validation/`](docs/validation/) | The Witness Stand: criteria, results, failures |
| [`docs/SCIENTIFIC_METHODOLOGY.md`](docs/SCIENTIFIC_METHODOLOGY.md), [`docs/DATA_SOURCES.md`](docs/DATA_SOURCES.md) | The method and every verified data fact |
| [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md), [`docs/DATA_CONTRACT.md`](docs/DATA_CONTRACT.md), [`docs/TECH_STACK.md`](docs/TECH_STACK.md) | System as built, the interface between workstreams, the stack |
| [`docs/DECISION_LOG.md`](docs/DECISION_LOG.md), [`docs/RISKS_AND_LIMITATIONS.md`](docs/RISKS_AND_LIMITATIONS.md) | Every decision with its approval status; risks and limits |
| [`docs/NUMBER_INVENTORY.md`](docs/NUMBER_INVENTORY.md) | Every number the app shows and how it is derived and rounded |
| [`api/README.md`](api/README.md), [`app/README.md`](app/README.md), [`data/README.md`](data/README.md) | The API, the app, the data |
| [`docs/PROJECT_PLAN.md`](docs/PROJECT_PLAN.md), [`docs/TASK_TRACKER.md`](docs/TASK_TRACKER.md), [`docs/TEAM_ROLES.md`](docs/TEAM_ROLES.md), [`docs/TEAM_WORKFLOW.md`](docs/TEAM_WORKFLOW.md), [`CONTRIBUTING.md`](CONTRIBUTING.md) | Plan, tasks, roles and how the team works |
| [`docs/RESEARCH_SUMMARY.md`](docs/RESEARCH_SUMMARY.md), [`docs/PROGRESS_LOG.md`](docs/PROGRESS_LOG.md) | Discovery research; dated progress |

## Team

Three members; see [`docs/TEAM_ROLES.md`](docs/TEAM_ROLES.md): **Member 1** Project Lead and reviewer; **Member 2** data engineering and scientific analysis (`pipeline/`); **Member 3** application development and UI (`api/`, `app/`).

## Data acknowledgement

We acknowledge the use of data and imagery from NASA's Fire Information for Resource Management System (FIRMS) (https://earthdata.nasa.gov/firms), part of NASA's Earth Science Data and Information System (ESDIS), and from LANCE. FIRMS data are provided "as is".

## Repository visibility

This repository is **private**. Collaborators are added by the Project Lead only. Making it visible to judges before submission is an open decision (see `docs/DECISION_LOG.md`, D-014).
