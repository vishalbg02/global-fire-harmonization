# Task prompt: T-042 Performance and accessibility pass

> Prepared for: Member 3 · Date: 2026-11-14 · Based on main @ ea95601
> Source of truth: docs/TASK_TRACKER.md row T-042 (keyboard navigation; colour-blind-safe check), the Lead's assignment in PR #38 ("keyboard navigation, colour-blind check of every ramp, and the >500 kB chunk warning (code-split the map and charts). Report before/after numbers"), the Lead's review of PR #47 (custom-area speed target) and `docs/prompts/MEMBER_3_APPLICATION_PROMPT.md` §18 and §19. This prompt adds no scope beyond them. The Lead marks the tracker row.

## 1. Objective

The app loads faster, runs smoothly on real data, and is usable without a mouse or without seeing colour, with before and after numbers measured, not claimed:
1. The production build has no chunk over 500 kB (the map and charts are code-split).
2. A custom area of country size answers in under 2 s (target set by the Lead), with a loading state while it computes.
3. Every interaction is keyboard-operable, focus is visible, contrast meets WCAG 2.1 AA, no information is carried by colour alone, and every colour ramp holds up under colour-blindness simulation.
4. The §18 targets are measured: a month change in about 1 s, smooth pan and zoom with a full month of real cells.

## 2. Baseline (measured on this machine on 2026-11-14, before any change)

- Build: one 2,816.61 kB chunk (819.67 kB gzip), and Vite warns that chunks are over 500 kB.
- Custom area (real products, `POST /api/series/custom`): country-sized box (about 107 cells) 3.2 to 3.5 s; about 4,700 cells 3.8 s; world 12.9 s. Every call scans the 146.6 million-row witness product.
- `GET /api/map` for one real month: about 0.58 s and 27.7 MB (56,238 cells, all contract fields).
- Not yet measured (to be measured first in this PR): month-change render time, pan and zoom frame rate, keyboard walkthrough, contrast, colour-blindness simulation.

## 3. In scope

- App: code-splitting (map with MapLibre and deck.gl, the ECharts panels, terra-draw, the methods page) with a loading state; a measured before/after of chunk sizes and first load.
- API: the custom-area speed work (see open question 1) and, if agreed, response compression (open question 6); a loading state in the app while a custom area computes.
- Accessibility: keyboard-only walkthrough of every view with the defects it finds fixed; visible focus; WCAG 2.1 AA contrast of text and controls; `prefers-reduced-motion`; no colour-only information; a colour-blindness check of every ramp and of the verdict, witness and calendar colours.
- Tests for what can be tested (contrast, ramp checks, tab order of the controls, loading states); a manual checklist and screenshots in the PR; `app/README.md`, `api/README.md` and `docs/RISKS_AND_LIMITATIONS.md` updated with measured numbers.

## 4. Out of scope

- Changes in `pipeline/`, `data/` or the contract (a faster `harmonize_area()` or a slimmer map payload are questions for the Lead and Member 2, see questions 1 and 6).
- New features (for example moving between map cells with the arrow keys): gaps found are reported, not built.
- Static fallback (T-043), polygon area (T-044).

## 5. Open questions, with defaults

1. **How to reach under 2 s for a custom area.** The Lead suggested a cached in-memory witness table or a per-area result cache. `harmonize_area()` opens the Parquet files itself, so an in-memory witness table cannot be passed in without a change in `pipeline/` (Member 2's). Default: (a) profile where the 3 s goes; (b) add an in-process result cache in the API keyed by the cell set and the products' modified times (repeat requests become instant, no pipeline change); (c) if the first request is still over 2 s, ask the Lead whether Member 2 should add an optional hook to `harmonize_area()` (a preloaded connection or table), rather than changing `pipeline/` myself. Nothing is cached incorrectly: the key includes the products' modified times and the method version, so a changed product never serves an old answer.
2. **Code splitting.** Default: `React.lazy` and `Suspense` for the map view, the calendar and witness charts, the draw tool and the methods page, plus a named vendor split only if needed; target: no chunk over 500 kB, reported in kB before and after, with the first-load time before and after on the real data.
3. **Colour-blindness check.** Default: simulate protanopia, deuteranopia and tritanopia with the published Machado, Oliveira and Fernandes (2009) matrices (a few lines of code, no new dependency) on every ramp stop and categorical colour; a Vitest test checks that ramps stay ordered by lightness and that the colours of the verdicts and of the witness lines stay distinguishable. The distinguishability threshold is my choice (stated in the test and the PR), not a standard; plus screenshots of the main views under each simulation.
4. **Keyboard.** Default: a skip link, a visible focus style, a documented tab order, and every control reachable; the map canvas itself has no cell-by-cell keyboard navigation, and the keyboard route to a place is the country search, the typed custom box, the calendar table view and the anomaly list. I report this limit rather than building a new feature.
5. **Contrast.** Default: compute the contrast ratios of the text and control colours in the stylesheet (both light and dark themes if the app has both) and fix any below 4.5:1 for text or 3:1 for controls.
6. **Response compression.** The real map month is 27.7 MB. Default: add the framework's gzip middleware to the API (no new dependency) and measure the transfer size and time; a slimmer map payload would need a contract change, which I do not make; I only report the numbers.
7. **Targets.** Month change about 1 s and smooth pan and zoom are the prompt's targets, not claims. Default: measure them in the browser on the real month (render time from the performance API; frame rate while panning) and report what is measured, including a miss.

## 6. Acceptance

- The build has no chunk over 500 kB, with before and after sizes in the PR.
- A country-sized custom area is under 2 s on the real products (repeat and, if question 1 allows, first request), with before and after times, and a visible loading state.
- A keyboard-only walkthrough of every view, a contrast table and a colour-blindness check are in the PR with their findings and the limits that remain; no defect found is left unreported.
- Lint, typecheck, tests, build and the API checks pass; screenshots go with the PR.
