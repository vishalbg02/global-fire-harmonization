# Task prompt: T-093 UI and UX excellence pass (the final experience)

> Prepared for: Member 2 · Date: 2026-11-15 · Based on main @ 076847e (plus the assignment commit 1f0fd12 of PR #99, which adds the tracker row and the brief)
> Source of truth: `docs/TASK_TRACKER.md` row T-093 and the Lead's brief `docs/prompts/T-093-UI-EXCELLENCE-PROMPT.md`. This prompt adds no scope beyond them; it is the plan the brief asks for in its phase 1.

## 1. Project context

The project answers the NASA Space Apps 2026 challenge "Harmonization of MODIS and VIIRS Hot Spots" (`docs/PROJECT_PLAN.md`): NASA FIRMS hotspots from Aqua MODIS, S-NPP VIIRS and NOAA-20 VIIRS are harmonized to one scale on a 0.5° grid, and every area and month gets a verdict with a probability, a 90% interval, the satellites used and the reasons. The pipeline, the products, the API and the web app exist and are validated for method 0.1.0 (38 results: 18 PASS, 18 FAIL, 2 INCONCLUSIVE). This task is the last pass over the web app only: it changes how the stored values are laid out and explained, and nothing about the values.

## 2. Task objective

When the task is done, the map page of `app/` has three zones (the Earth with one control dock, the answer panel, the timeline), layered help (a first-visit tour, "?" explainers, a Start-here state, a shortcuts sheet, one-line hints), a globe that is the default first view and behaves well (link sync, atmosphere, signal before noise at low zoom, fly-to, idle rotation, Satellite view in the dock), clear loading, empty and error states, a bottom sheet on tablets and phones, and it passes the brief's section 8. Every number on screen is still a stored value shown through the existing formatting helpers.

## 3. Assigned responsibility

- Task ID / priority: T-093 / P0
- Owner: Member 2 (the whole task, at the Lead's request of 2026-11-15)
- Reviewer and merger: Member 1 (Project Lead)
- Dependencies (MERGED): T-078, T-092

## 4. Relevant files and directories

- Read: `docs/prompts/T-093-UI-EXCELLENCE-PROMPT.md`, `docs/NUMBER_INVENTORY.md`, `docs/DATA_CONTRACT.md`, `api/README.md`, `app/README.md`, `pipeline/number_check.py`, `pipeline/number_check_app.mjs`, `app/src/**`.
- Create/modify: `app/src/**` (see the plan below), `app/README.md`, `docs/NUMBER_INVENTORY.md`, `docs/TASK_TRACKER.md` (row T-093 only), `docs/task-prompts/T-093-ui-excellence.md`, `docs/task-prompts/assets/T-093/**` (screenshots and GIFs), `docs/validation/T-093-ui-excellence.md` (the acceptance results).
- Not touched: `api/**`, `pipeline/**`, `data/**`, `app/src/content/featured.ts` (generated), `app/public/geo/**` (India's official boundary, D-033), `app/package.json` dependencies.

## 5. Approved technologies

The stack of D-008 as installed: React 19, Vite 8, TypeScript 7 (strict), MapLibre GL 6 (globe projection), deck.gl 9, ECharts 6, terra-draw, TanStack Query 5, IBM Plex Sans and Mono (self-hosted), Vitest 5, Oxlint. **No new runtime dependency.** Screenshots, GIFs and the axe-core run use tools kept outside the repository (a headless Chrome driver and axe-core 4.10.2), as T-074 did; nothing of them is committed or shipped.

## 6. Architecture and data contract

Contract 0.1.1 and the API stay as they are. The app keeps reading only the API or the offline copy (`app/src/api/client.ts`, `staticData.ts`). The helpers that `pipeline/number_check_app.mjs` imports keep their names and behaviour: `components/map/format.ts`, `components/anomalies/rankings.ts`, `components/methods/validationFormat.ts`, `state/bbox.ts`, `components/map/scale.ts` (`sharedMax`), `components/calendar/grid.ts` (`maxActivity`).

## 7. Inputs

The running API on the real products (`metadata.synthetic=false`, method 0.1.0, 2002-07 to 2026-11, provisional 2026-08 to 2026-11): `/api/meta`, `/api/entities`, `/api/series`, `/api/evidence`, `/api/anomalies`, `/api/map/cells`, `/api/validation`, `/api/export.csv`; NASA GIBS tiles (Blue Marble, Aqua MODIS true colour); the approved texts in `app/src/content/*.ts`.

## 8. Expected outputs

The redesigned map page, its tests, the updated number inventory, the acceptance report with real results, and the screenshots and GIFs the brief lists.

## 9. Implementation plan (phases; one commit, or a few, per phase)

Design direction (the brief, section 5): a scientific instrument. Light instrument panels (the existing tokens, verdict colours and contrast tests are kept) around a dark "space" stage that holds the Earth. One accent (the existing vermillion) for the selection, the current month and the primary action. Plex Sans for text, Plex Mono with tabular figures for every number, the 12/14/16/20/28/40 scale, a 4/8 px grid, 1 px rules, radius at most 4 px, one elevation for panels that float over the map.

1. **Audit and plan.** Done on `main` @ 076847e at 1440x900 with the real products; screenshots in `docs/task-prompts/assets/T-093/before/`. Measured: the first visit puts the top of the map at 666 px (the "How to read this" panel is above it) and the page is 3,387 px tall; 47 buttons, inputs and selects on the map page (48 with the panel's button), 32 to 38 of them in the first viewport; the right column is 1,590 px tall for Indonesia 2015-09; four overlays sit on the map. **The Flat/Globe link fault did not reproduce in a clean browser profile** (`?month=2026-10&globe=1` gave the globe and a checked Globe radio). The code shows why it can fail: the shape lives in three places (the map component's state, the map's projection set once on `load`, and the link, which both `App.tsx` and `MapView.tsx` rewrite), so a re-mount, a slow `load` or a rewrite in between can leave them apart. Phase 3 makes the link-backed state the one source and tests it.
2. **Foundations.** `styles/tokens.css` (stage and elevation tokens, tidy-up), `styles/layout.css` and `index.css` (three zones, dead rules removed), `App.tsx` (the shell: slim header, stage with the dock, answer panel 380 px, timeline under the map, Details below), new `components/dock/` (area search; Country / Rectangle / Polygon; Flat / Globe; Satellite view with its date chip and day picker; Layers: Verdict / Activity and Raw / Harmonized; typed custom area behind "Type an area"), new `state/mapView.ts` (shape, Satellite view, day, "show all verdicts": one state, kept in the link), `components/map/` overlays reduced to the legend strip (bottom left) and the credit line (bottom right), `components/layout/Header.tsx` (wordmark, purpose, Methods and validation, Help).
3. **Earth** (`components/map/`, `state/mapView.ts`): the link sync fix with a test; globe by default on a first visit at world view (silent fallback to flat when the globe cannot render); dark space behind the globe and an atmosphere halo (MapLibre's sky where it works on the globe, a CSS radial background otherwise); at zoom 3 and below only ABOVE and BELOW cells at full strength, the other three nearly transparent, with "Show all verdicts" in the legend; fly-to of about 1.2 s on selection (instant under reduced motion); slow idle rotation after 8 s on the globe at world view, stopped by any interaction, off under reduced motion, with a pause control; the hovered cell highlighted; a slim progress line while a month loads.
4. **Answer panel** (`components/summary/`, `components/evidence/`, `components/layout/Story*.tsx`, `components/ui/Tabs.tsx`, `components/analytics/` caption only): the hierarchy verdict, % of normal (Mono 40 px), probability sentence, interval bar (estimate, 90% interval and the p25 to p75 normal band, stored values only), sparkline, reasons as chips that open the approved sentence, source line, actions (CSV, Copy link, Compare with…); the story as a quiet collapsible card; sticky Details tabs that remember the last tab; the one-line takeaway under the raw-versus-harmonized chart.
5. **Timeline** (new `components/timeline/`, reusing `map/monthPicker.ts`, `MonthPicker.tsx`, `playback.ts`): a 2002 to 2026 strip with year ticks, the selected area's monthly estimate drawn faintly behind it from the series already loaded, the current month marked, provisional months shaded and labelled, satellite-join ticks (S-NPP 2012-01, NOAA-20 2018-04, from `content/witnessTimeline.ts`), Play / Pause and "Choose a month".
6. **Help** (new `components/help/`, `content/help.ts`): the guided tour (five steps, anchored, skippable, Esc, keyboard, shown once on a first visit without link parameters, stored in `localStorage` inside try/catch, reopened by Help); "?" explainers from `GLOSSARY` with a "Learn more" link to the methods anchor; the Start-here state (three questions built from `content/featured.ts`, plus "Search any country"); the shortcuts sheet (`?`); one-line contextual hints.
7. **States, responsive, accessibility, performance:** skeletons, plain-word errors with Retry, toasts ("Link copied", "CSV downloaded"), the bottom sheet at 768 and 375 (drag handle, three heights), the dock collapsed to icons there, axe-core, Lighthouse, the bundle size against `main`.
8. **Verification:** the commands in section 12, the number inventory, the offline copy built and opened, the browser pass, screenshots and GIFs, the acceptance report.

Phases 3, 4 and 6 run in parallel after phase 2 is committed (they own different folders, as the brief says); phase 5 runs beside them; the whole suite runs after they are brought together.

Scientific rules that apply to every phase: display only; every number through the existing helpers; missing data shown as missing, never 0 and never interpolated (the timeline's background line has gaps where the series has none); a hotspot is not a fire or burned area; "cannot determine" is styled as a result; no cause, forecast or accuracy claim in any new text; imagery is context, not data.

## 10. Constraints: do not modify

- Do not change the tech stack, architecture, scientific methodology or data contract.
- Do not edit files outside section 4 "Create/modify". Do not touch `api/`, `pipeline/`, `data/`.
- No number, verdict, probability, threshold or rule changes; no sample or invented numbers anywhere, in help texts and screenshots included.
- India's official boundary (D-033) and the credits (NASA FIRMS, NASA GIBS, Natural Earth, method version) stay as they are and stay visible.
- No secrets, no raw or interim data, no direct pushes to main, no self-merge. No AI names or attribution anywhere (D-020).

## 11. Acceptance criteria

Section 8 of the brief, measured:

- `npm test`, `npm run typecheck`, `npm run lint` (0 warnings) and `npm run build` pass; `pytest pipeline/tests api/tests` passes.
- `python pipeline/number_check.py` reports 0 mismatches; `docs/NUMBER_INVENTORY.md` has a row for every display added or moved.
- axe-core: 0 A/AA violations on the map, methods and help views. Lighthouse accessibility at least 95; performance noted.
- First-time-user test, the five tasks with their limits (30, 30, 60, 30 and 20 s). It is run as a **simulated** walk-through in a real browser from a fresh profile, timed and reported as simulated, not as a test with a person.
- Screenshots at 1440x900, 1280x720, 1024, 768 and 375 of: the first visit with the tour, the world on the globe, Indonesia 2015-09, Australia 2019-12, Canada 2023-08, the methods page. GIFs of the tour, fly-to and globe rotation, and timeline scrubbing.
- Behaviour: the Flat/Globe link sync is tested; the tour shows once and Help reopens it; shared links open without the tour; reduced motion turns off all animation; the offline copy opens and works (imagery falls back).
- At most about 15 controls visible at first glance at 1440x900; first meaningful map within 2.5 s on the local API; the bundle not more than 15% larger than `main` without a reason.

## 12. Required tests

```bash
cd app && npm test && npm run typecheck && npm run lint && npm run build
.venv/Scripts/python -m pytest pipeline/tests api/tests -q
.venv/Scripts/python pipeline/number_check.py
```

New unit tests: the map-view link state (shape, Satellite view, day, show-all, defaults, old links); the low-zoom cell strength rule; the interval bar geometry; the timeline geometry (ticks, provisional span, join marks, gaps); the tour state (first visit, link parameters, dismissal, storage blocked); the shortcut map; the help content (every explainer has a glossary text and a methods anchor; no forbidden claim in any new text); the Start-here questions (built from `featured.ts`, never typed). Browser checks: axe-core on the three views, the five sizes, reduced motion, the offline copy.

## 13. Documentation updates

`docs/TASK_TRACKER.md` row T-093 (IN_PROGRESS, then IN_REVIEW with the PR link); `docs/NUMBER_INVENTORY.md`; `app/README.md` (layout, link parameters, help, shortcuts); `docs/validation/T-093-ui-excellence.md` (actual results, failures included).

## 14. Git branch and PR instructions

- Branch: `frontend/T-093-ui-excellence`, created from the latest `main`, with the assignment commit of PR #99 underneath so the tracker row and the brief are present.
- First commit: this file and the "before" screenshots. Draft PR "T-093: UI and UX excellence pass" opened early; a commit per phase; Ready for review only when sections 11 and 12 are satisfied.
- Never merge; the Project Lead reviews and merges. Own Git identity; no AI names or attribution (D-020).

## 15. Open questions for the Lead (each has the default that is built unless the Lead says otherwise)

1. **What does the answer panel show before anything is chosen?** Default: on a visit with no `area` and no `month` in the link, the Start-here state (three questions from the featured stories, "Search any country", and "Show the whole world for <latest determinable month>"). The world's own answer appears as soon as the world, a month or a story is chosen, and for every link that carries a month. Reason: the world's first answer is "cannot determine" for a provisional month, which is a poor first lesson.
2. **Globe by default, and old links.** Default: the globe when the link has no parameters at all; any link without `globe=` that carries other parameters keeps the flat map it had when it was shared; once the user picks a shape the link says `globe=1` or `globe=0`.
3. **"Signal, not noise" numbers.** Default: at zoom 3.0 and below, ABOVE and BELOW cells keep the full opacity and WITHIN, CANNOT_DETERMINE and NO_DETECTED_ACTIVITY are drawn at 12% opacity; from zoom 3.0 to 4.0 they fade up to the full opacity; "Show all verdicts" in the legend draws all five at full strength at every zoom and is kept in the link as `allv=1`. Display only: the tooltip, the cell card and the panel are unchanged.
4. **Where the Details tabs sit.** Default: below the first viewport at full width (the calendar and the analytics charts need the width), reached by scrolling or by "Details" in the answer panel, with a sticky tab bar. The first viewport holds the Earth, the timeline and the answer with no page scroll.
5. **The old "How to read this" panel.** Default: it no longer opens over the map. Its approved steps, verdict list and glossary are kept word for word inside the Help sheet, which the Help button and the last tour step open.
6. **New help texts.** The tour steps, three explainers that have no glossary entry yet ("probability", "no detected activity", "Satellite view"), the hints and the takeaway under the raw-versus-harmonized chart are new sentences in `content/help.ts`, written in the voice of `plainLanguage.ts`, tested for forbidden claims, and listed in the PR for the Lead's wording review.
7. **Theme.** Default: light panels around a dark Earth stage (the existing tokens and verdict colours unchanged), one theme; no dark mode of the panels in this task.
8. **The first-time-user test** is a simulated walk-through (see section 11). The PR says so next to the times.

If anything needs an API addition or a contract change, work on that part stops and it is described under "Scope issues" in the PR.
