# Global Fire Harmonization (working name: *Many Witnesses*)

NASA Space Apps Challenge 2026 project for the challenge
**[Harmonization of MODIS and VIIRS Hot Spots](https://www.spaceappschallenge.org/2026/challenges/modis-and-viirs-hot-spots/)**.

> **Status (2026-11-14):** Planning and repository setup. **No application code yet.**
> The technology stack and data contract are **PROPOSED and awaiting Project Lead approval.**
> See [`docs/HANDOFF.md`](docs/HANDOFF.md) for the exact current state.

## What we are building

This is a global web platform that turns NASA FIRMS active-fire hotspots into one harmonized monthly record of fire activity, running from July 2002 to the latest available data.

- The record combines three satellite "witnesses": **Aqua MODIS**, **Suomi-NPP VIIRS** and **NOAA-20 VIIRS**.
- Users can explore it for any grid cell, country, continent or custom area.
- The platform separates **real changes in fire activity** from **apparent changes caused by sensors**: different resolution and sensitivity, satellites joining or leaving, orbit drift, and data gaps.
- Every month gets a verdict: **above normal / below normal / within normal / cannot determine**. Each verdict comes with an uncertainty estimate and an evidence panel.
- A published validation suite, the **Witness Stand**, sits behind the verdicts. It reports failures as well as successes.

The challenge asks for a burning-activity calendar that combines MODIS's long history with VIIRS's continuity and detail. It also asks users to be able to compare current activity against the historical median and download CSV data.

## Core principle

A hotspot is a satellite pixel flagged as containing fire. It is **not** a fire count, a perimeter or burned area. No satellite tells the whole truth, so we weigh each one as a witness according to what it could actually see, and we say "cannot determine" when the evidence is insufficient.

## Documentation map

| Document | Purpose |
|---|---|
| [`CLAUDE.md`](CLAUDE.md) | Instructions for AI assistants and rules for resuming work |
| [`CONTRIBUTING.md`](CONTRIBUTING.md) | Git workflow, PR process, review checklist |
| [`docs/HANDOFF.md`](docs/HANDOFF.md) | **Start here when resuming**: exact current state |
| [`docs/PROJECT_PLAN.md`](docs/PROJECT_PLAN.md) | Vision, scope, features, milestones, 36-hour schedule |
| [`docs/TECH_STACK.md`](docs/TECH_STACK.md) | Technology recommendation (PROPOSED) |
| [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) | Components, data flow, integration boundaries (PROPOSED) |
| [`docs/DATA_CONTRACT.md`](docs/DATA_CONTRACT.md) | Data formats exchanged between workstreams (PROPOSED) |
| [`docs/SCIENTIFIC_METHODOLOGY.md`](docs/SCIENTIFIC_METHODOLOGY.md) | Harmonization science, uncertainty, limitations |
| [`docs/DATA_SOURCES.md`](docs/DATA_SOURCES.md) | NASA data sources, access, verified facts |
| [`docs/VALIDATION_PLAN.md`](docs/VALIDATION_PLAN.md) | Witness Stand cases, pass/fail criteria, results |
| [`docs/TEAM_ROLES.md`](docs/TEAM_ROLES.md) | Responsibilities, deliverables, handoffs |
| [`docs/TASK_TRACKER.md`](docs/TASK_TRACKER.md) | Tasks, owners, status, acceptance criteria |
| [`docs/DECISION_LOG.md`](docs/DECISION_LOG.md) | Every important decision and its approval status |
| [`docs/RISKS_AND_LIMITATIONS.md`](docs/RISKS_AND_LIMITATIONS.md) | Risks, limitations, fallbacks |
| [`docs/PROGRESS_LOG.md`](docs/PROGRESS_LOG.md) | Dated progress |
| [`docs/RESEARCH_SUMMARY.md`](docs/RESEARCH_SUMMARY.md) | Discovery research, competitor analysis, sources |
| [`data/README.md`](data/README.md) | Where datasets live and how to obtain them |

## Setup

No application exists yet, so there is nothing to install. Setup instructions will be added once the stack is approved (see `docs/TECH_STACK.md`). Planned prerequisites, subject to approval:

- Python 3.12–3.14
- Node.js 22 LTS or 24 LTS (Node 20 is end-of-life)
- A free NASA FIRMS **MAP_KEY** for the 2026 API data. Copy `.env.example` to `.env` and set your key there. **Never commit `.env`.**
- About 60 GB of free disk space for the raw archive (≈9.1 GB zipped, ≈41 GB unzipped; see `docs/DATA_SOURCES.md`)

## Team

There are three members; see [`docs/TEAM_ROLES.md`](docs/TEAM_ROLES.md).

- **Member 1:** Project Lead / CTO, who supervises and reviews
- **Member 2:** Data engineering and scientific analysis
- **Member 3:** Application development and UI

## Data acknowledgement

We acknowledge the use of data and imagery from NASA's Fire Information for Resource Management System (FIRMS) (https://earthdata.nasa.gov/firms), part of NASA's Earth Science Data and Information System (ESDIS), and from LANCE. FIRMS data are provided "as is".

## Repository visibility

This repository is **private**. Collaborators are added by the Project Lead only. Making the repository visible to judges before submission is an open decision (see `docs/DECISION_LOG.md`, D-014).
