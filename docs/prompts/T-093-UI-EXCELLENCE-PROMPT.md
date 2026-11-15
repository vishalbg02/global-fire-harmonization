# T-093: UI and UX excellence pass (the final experience)

**Owner:** Member 2 (Kaushik), the whole task. **Assigned by:** the Project Lead, 2026-11-15.
**Branch:** `frontend/T-093-ui-excellence`. One branch, one PR (commit per phase so the Lead can review step by step).
**Use this file as the prompt for your coding agent.** Read it fully before writing any code. Work in phases. Run the agents in parallel only where their files do not overlap.

---

## 0. Your role and the bar

You are the lead product designer and senior frontend engineer for a NASA Space Apps 2026 project. You are finishing the interface that judges, emergency managers, scientists and journalists will use.

The Lead's words:
- "the UI is not good enough"
- "the globe is not good enough"
- "it is not user-friendly"
- "a first-time user can't understand how to use it"
- "it must never look AI-generated; fully professional; the best"

Your job is to make this the most usable, trustworthy and beautiful scientific Earth-data tool a judge has seen this weekend. **The bar:** a first-time visitor understands what the app does in **10 seconds**, answers "was fire activity in X unusual in month Y?" in **30 seconds**, and never feels lost.

## 1. The product, in one paragraph

NASA FIRMS satellites (MODIS on Aqua; VIIRS on S-NPP and NOAA-20) detect fire hotspots. Their raw counts jump whenever a satellite joins or leaves, so raw records lie. We harmonize them to one scale (Aqua-equivalent fire-active cell-days) on a 0.5° grid, 2002-07 to 2026-11. For every area and month we give a **verdict**: above normal, within normal, below normal, cannot determine, or no detected activity. Each verdict comes with a probability, a 90% interval, the satellites used, the reasons, and the sources. We publish our own validation (38 results: 18 PASS, 18 FAIL, 2 INCONCLUSIVE), failures included.

The one question every screen serves: **"Did fire activity really change here, or only the satellites watching it?"**

## 2. Hard rules (non-negotiable; a PR that breaks one is rejected)

1. **No number, verdict, probability, threshold or rule changes.** Display only. Every number comes from the API (or the offline copy) exactly as stored. After your work, `python pipeline/number_check.py` must report **0 mismatches**, and `docs/NUMBER_INVENTORY.md` is updated for every display you add or move.
2. **Real data only.** No sample, placeholder or invented numbers anywhere: UI, onboarding, tooltips, screenshots. Synthetic fixtures stay in tests, labelled SYNTHETIC.
3. **The data contract and the API stay as they are** (`docs/DATA_CONTRACT.md`, `api/README.md`). If you truly need an API addition, stop and ask the Lead on the PR.
4. **Scientific honesty in every word.** Hotspots are not fires and not burned area. "Cannot determine" is a result, not an error. Never imply a cause, a forecast or global accuracy. Reuse the approved texts in `app/src/content/*.ts`. New texts go in `content/` with tests (no forbidden claims), in a plain, factual voice.
5. **India's official boundary** (D-033) stays exactly as it is. Sources and credits stay visible (NASA FIRMS, NASA GIBS, Natural Earth, method version).
6. **Accessibility:** WCAG 2.2 AA.
   - Keyboard-only path for every action.
   - Visible focus.
   - Colour is never the only cue: icons and text stay with the verdict colours.
   - `prefers-reduced-motion` respected.
   - axe-core: 0 A/AA violations. Lighthouse accessibility ≥ 95.
7. **Performance:**
   - First meaningful map ≤ 2.5 s on the local API.
   - No layout shift when panels load.
   - Month switch feels instant (keep the T-073 prefetch).
   - The bundle must not grow by more than 15% without a reason in the PR.
8. **Offline copy** (`api/fire_api/static_export.py`, `app/src/api/staticData.ts`) keeps working. Imagery falls back to the plain background, as today.
9. **No new runtime dependency** without the Lead's approval on the PR (the stack is D-008). React, MapLibre 6, deck.gl 9, ECharts 6, terra-draw and IBM Plex are already here. Use them.
10. **Git and process:** your own Git identity, Conventional Commits with `(T-093)`, no AI attribution anywhere, no push to `main`, the Lead merges. Tests, typecheck, lint (0 warnings) and build must pass.

## 3. What exists (do not rebuild what works; elevate it)

- **Stack:** React + Vite + TypeScript strict; MapLibre 6 (with globe projection) + deck.gl 9 cells; ECharts 6; IBM Plex Sans and Mono, self-hosted.
- **Design tokens:** `app/src/styles/tokens.css`; layout in `app/src/styles/layout.css` (about 2,000 lines of CSS in total).
- **Layout** (`App.tsx`): header, toolbar (area search, month control with Play and "Choose a month", Raw/Harmonized, Verdict/Activity, "Draw or type an area", Copy link), story chips, map with overlays (mode switch Country/Rectangle/Polygon, Map view panel with Satellite view and Flat/Globe, legend, cell card, credit), right column (summary card with sparkline, top anomalies), and a tab card (Calendar, Satellites, Evidence in detail, All anomalies, Analytics).
- **Map:** `components/map/` (`MapView.tsx`, `ImageryControls.tsx`, `gibs.ts`, `imagery.ts`, `mapOverlays.tsx`, `Legend.tsx`, `CellInfo.tsx`, `MonthSelector.tsx`, `MonthPicker.tsx`).
- **Onboarding today:** `layout/HowToRead.tsx`, a text panel built from `content/plainLanguage.ts`.
- **Stories:** `content/featured.ts` (generated by `pipeline/featured_stories.py`; do not edit by hand) and `layout/StoryChips.tsx` / `StoryCaption.tsx`.
- **Methods page:** `components/methods/`, with the T-089 redesign.

## 4. The Lead's audit of `main` (2026-11-15, real browser, 1440x900): fix all of these

1. **First visit is a wall of text.** "How to read this" opens as a long multi-column block above the map and pushes the map below the fold. A newcomer reads paragraphs instead of seeing the Earth.
2. **Too many controls at once: 47 buttons, inputs and selects are visible.** The toolbar wraps, the story chips add a third row, and the map carries 4 overlays: mode switch, Map view panel, legend and credit. Nothing tells the user what to do first.
3. **The globe is not good:**
   - **The Flat/Globe switch can fail.** With `?globe=1` the URL says globe but the radio shows Flat and the map stays flat (`MapView.tsx`, `setProjection` around line 412; the link state and the radio are out of sync).
   - **At world zoom, cells bury the Earth.** Grey "within normal" and sand "no detected activity" cells cover almost every land pixel, so NASA's Blue Marble is barely visible and the signal (above/below normal) drowns in noise.
   - The globe has no "Earth feeling": no atmosphere or space background, no smooth fly-to on selection, no idle motion, and nothing that invites the user to turn it.
4. **The map overlays compete.** The legend, Map view panel, credit and hints sit on top of the data, and on smaller laptops they cover the area the user selected.
5. **The right column is long.** Summary card, sparkline, source text, reasons, CSV text and anomalies stack into a tall scroll. The most important line (verdict, % of normal, probability) is good, but what follows has no hierarchy.
6. **The time control is crowded:** Play, ⏮, ◀, slider, ▶, ⏭, label, Provisional badge and "Choose a month" in one row. A newcomer doesn't know 2002 to 2026 is the range, or what Provisional means.
7. **There is no guidance at the moment of need.** Terms like "% of normal", "90% interval", "Aqua-equivalent cell-days" and "cannot determine" have no inline explanation where they appear.
8. **Empty, loading and error states** are plain text. Imagery or a month can load slowly with no clear feedback.

## 5. Design direction: a scientific instrument, not a template

**Mood:** NASA Worldview / Earthdata, a mission-control console, and the restraint of a top newspaper's data desk (Reuters Graphics, the FT). Calm, precise, confident. The Earth is the hero; the interface is the instrument around it.

**Never (each of these reads as "AI-generated"):**
- gradients on UI chrome, glassmorphism, neon glows
- purple or blue SaaS palettes
- emoji in UI
- "✨" or "🚀" anything
- icon-card feature grids
- marketing headlines ("Unlock insights…")
- rounded-everything with drop shadows
- generic stock illustrations
- lorem-like filler
- centred hero text over a gradient
- excessive animation
- random accent colours

**Always:**
- **Colour:** the verdict palette (Okabe-Ito based, colour-blind safe; keep the existing values) plus a disciplined neutral ramp. One accent, the existing vermillion, used only for the current selection, the current month and the primary action. Two surface tones at most.
- **Type:** IBM Plex Sans for UI and IBM Plex Mono with tabular figures for every number. A strict scale: 12/14/16/20/28/40. Numbers are the heroes. Units are always written, in a quieter weight.
- **Space and structure:** a 4/8 px grid, thin 1 px rules, radius at most 4 px, no shadows except one subtle elevation for floating map panels.
- **Density:** high but ordered, like an instrument panel; every pixel earns its place. Remove duplication.
- **Motion:**
  - 150–250 ms, ease-out, purposeful only: panel reveal, fly-to, verdict change.
  - Never decorative.
  - Everything off under `prefers-reduced-motion`.
- **Voice:** plain, exact, sourced. Label claims ([VERIFIED] where the content already does).

## 6. What to build

### 6.1 Information architecture: three zones, progressive disclosure

- **Zone A, the Earth (hero):** the map/globe takes most of the viewport. **One consolidated floating control dock** on the map (top-left), with:
  - the area search
  - Country / Rectangle / Polygon
  - Flat / Globe
  - Satellite view
  - Layers (Verdict / Activity, Raw / Harmonized)

  The legend lives as a compact, collapsible strip (bottom-left). The credit is a small line (bottom-right). Nothing else floats over the data.
- **Zone B, the answer (right panel, fixed width about 380 px):**
  1. the area and month
  2. the verdict badge, the big % of normal and the probability sentence
  3. the interval, with a tiny inline interval bar against the normal range
  4. the sparkline with the normal band
  5. the "Why" reasons as chips that expand
  6. the source line
  7. actions (CSV, copy link)

  Everything else goes into **Details** tabs below (Calendar, Satellites, Evidence, Anomalies, Analytics).
- **Zone C, time (bottom of the map, full width):** a **timeline scrubber**:
  - a slim strip from 2002 to 2026 with year ticks
  - a faint sparkline of the **world** (or the selected area's) monthly activity drawn behind it, from the existing `/api/series` data, so users see seasons and big years
  - the current month marked
  - provisional months shaded and labelled
  - satellite joins marked (S-NPP 2012-01, NOAA-20 2018-04) as small labelled ticks
  - Play/Pause and "Choose a month" kept (reuse T-087)
- **Header:** the wordmark, a one-line purpose, "Methods and validation" and "Help" (opens the guide). Keep it slim.
- **Target:** at most about 15 controls visible at first glance on 1440x900. The rest is one click away and discoverable.

### 6.2 Onboarding and help: "how to use", done properly

Replace the wall of text with layered help that never blocks:
1. **A first-visit guided tour** (4–5 steps, anchored coach marks on the real UI):
   1. "Pick a place" (search or click the map)
   2. "Pick a month" (the timeline)
   3. "Read the verdict" (the answer panel)
   4. "Why this verdict" (reasons and evidence)
   5. "Raw vs harmonized" (point at Analytics or the toggle)

   Each step is one sentence plus "Next". Skip any time, Esc closes, it's keyboard accessible, and it focuses the anchored element. It shows only on a first visit without link parameters, and the dismissal is stored in `localStorage` (inside try/catch). A **"Help"** button reopens it.
2. **Inline "?" explainers** next to "% of normal", "90% interval", "probability", "Aqua-equivalent cell-days", "cannot determine", "no detected activity", "provisional", "Raw vs Harmonized", "Satellite view". Each is a popover with 1–2 sentences from `content/plainLanguage.ts` (`GLOSSARY`) and a "Learn more" link to the methods anchor.
3. **A "Start here" empty state** when nothing is selected: three example questions as buttons, built from the featured stories (e.g. "Was Indonesia's September 2015 unusual?"), plus "Search any country".
4. **Keyboard shortcuts sheet** (`?` key): ←/→ month, PageUp/PageDown year, Space play/pause, G globe, S satellite view, / search, Esc close.
5. **Contextual one-line hints**, e.g. the first time Globe is chosen: "Drag to turn the Earth; Ctrl + scroll to zoom".

### 6.3 The Earth experience

Make the globe the most beautiful part:
- **Fix the Flat/Globe sync bug** (§4.3): the radio, the map projection and `?globe=1` always agree, on load and on change. Add a test.
- **Globe by default on the first visit at world view** (the Flat switch stays, and the user's choice is remembered in the link). If the globe can't render (WebGL limits), fall back to flat silently.
- **Space and atmosphere:** a dark space background behind the globe and a subtle atmosphere halo. Use MapLibre's sky/fog options if available in v6; otherwise use a CSS radial background behind the canvas. No stars clip art.
- **"Signal, not noise" at low zoom:** at zoom ≤ 3, draw only ABOVE and BELOW cells at full strength, and make WITHIN, CANNOT_DETERMINE and NO_DETECTED_ACTIVITY nearly transparent (or outline-only), so Blue Marble shows and the anomalies pop. Give full detail as the user zooms in, and a legend toggle "Show all verdicts". This is display only; the stored verdicts are unchanged and every cell is still in the tooltip and the panel.
- **Fly-to:** selecting a country or story animates smoothly (about 1.2 s) to fit the area (polygon bounds; T-085 logic). It's instant under reduced motion.
- **Idle rotation:** on the globe at world view, a very slow rotation after 8 s idle that stops on any interaction. It's off under reduced motion, and the user can pause it.
- **Satellite view:** integrate it into the dock as a clear toggle with the date chip ("Aqua MODIS true colour, 15 Sep 2015", with the day picker). Cells over it get a thin dark casing so they read over clouds.
- **Hover and select:** keep the country hover outline and verdict readout, and add a subtle highlight of the hovered cell. The selected area keeps India's official outline logic.

### 6.4 The answer panel and the details

- **Verdict hierarchy:**
  1. verdict (badge + icon)
  2. % of normal (Mono, 40 px)
  3. the probability sentence
  4. **interval bar:** a small horizontal bar showing the estimate, its 90% interval and the normal band (p25–p75), so "above normal" is *visible*

  Use only existing values.
- **Reasons** as compact chips (icon + short label) that expand to the approved sentence.
- **Story mode:** when a featured story is active, the caption appears as a quiet "Story" card with its [VERIFIED] label. It's collapsible.
- **Details tabs:** keep the five, with sticky tab headers, and remember the last tab. Analytics keeps its five views. Give the raw-vs-harmonized chart a one-line takeaway caption from content ("The raw count jumps in 2012 when S-NPP joins; the harmonized estimate stays on one scale.").
- **Compare** (T-090) is reachable from the answer panel ("Compare with…").

### 6.5 States, feedback, polish

- **Skeletons:** for the answer panel and charts (no spinners in the middle of text). A slim progress line on the map while a month loads. Imagery loading and failure states are explained in one line.
- **Errors** in plain words, with a retry. "Cannot determine" is styled as a result, not an error.
- **Toasts:** "Link copied" and "CSV downloaded".
- **Consistent hover, focus and active states** on every control, from tokens.
- **Responsive:** at 1440, 1280x720 (projector) and 1024 the three zones fit with no page scroll for the main answer. At 768 and 375, the answer panel becomes a bottom sheet over the map (drag handle, three heights), the dock collapses to icons with labels on long-press/focus, and the timeline stays visible.

## 7. Working plan (phases, with a commit at the end of each)

1. **Audit and plan (30 min):**
   - Run the app (README; API `--app-dir api`, products in `data/products`).
   - Reproduce §4 with screenshots.
   - Write `docs/task-prompts/T-093-ui-excellence.md`: your plan, the files per phase and any open questions. Post open questions on the PR (default if not answered).
2. **Foundations:** tokens tidy-up, layout skeleton (zones A/B/C), control dock, legend strip, credit line. Remove duplication.
3. **Earth:** the globe sync fix, globe default, atmosphere, signal-not-noise, fly-to, idle rotation, satellite view in the dock.
4. **Answer panel:** hierarchy, interval bar, reasons chips, story card, details tabs.
5. **Timeline:** scrubber with the activity sparkline, satellite-join ticks, provisional shading, Play and the picker.
6. **Help:** guided tour, "?" explainers, Start-here state, shortcuts sheet, contextual hints.
7. **States, responsive, accessibility, performance:** skeletons, toasts, bottom sheet, axe/Lighthouse, bundle check.
8. **Verification:** tests, `number_check.py` (0 mismatches), `NUMBER_INVENTORY.md` updated, the offline copy built and opened, the browser pass below, screenshots and GIFs.

**Parallel agents:** phases 3, 4 and 6 can run in parallel *after* phase 2 lands in your branch (they touch different folders: `map/`, `summary/` and `evidence/`, and a new `help/`). Merge them back carefully; run the whole suite after each merge.

## 8. Acceptance: the Lead checks all of this before merging

**Automated:**
- vitest, typecheck, lint (0 warnings), build pass
- pytest for pipeline and API pass
- `number_check.py`: 0 mismatches
- axe: 0 A/AA violations on the map, methods and help views
- Lighthouse accessibility ≥ 95 and performance noted

**First-time-user test** (do it with someone who has never seen the app, or simulate honestly, and report times):
1. Find whether Indonesia, September 2015 was unusual: ≤ 30 s.
2. Say why the verdict is what it is: ≤ 30 s.
3. Find the month with Canada's highest activity in 2023: ≤ 60 s.
4. Show the raw-vs-harmonized difference: ≤ 30 s.
5. Turn the globe and switch on Satellite view: ≤ 20 s.

**Visual:** screenshots at 1440x900, 1280x720, 1024, 768 and 375 for:
- the first visit with the tour
- the world on the globe
- Indonesia 2015-09
- Australia 2019-12
- Canada 2023-08
- the methods page

Plus GIFs of the tour, fly-to and globe rotation, and timeline scrubbing.

**Behaviour:**
- The Flat/Globe link sync is tested.
- The tour shows once, and Help reopens it.
- Shared links open without the tour.
- Reduced motion turns off all animation.
- The offline copy opens and works (imagery falls back).

**Honesty:**
- Every number on screen is in `NUMBER_INVENTORY.md`.
- Every new text is in `content/` with tests.
- No forbidden claim.
- India's official boundary is unchanged.

## 9. Deliverable

One PR, `T-093: UI and UX excellence pass`, containing:
- the plan file
- commits per phase
- the PR description with before/after screenshots for each §4 item, the acceptance results (numbers, times, scores), the real-data statement ("Real data: `metadata.synthetic=false`, no synthetic banner shown, no fixture imported outside tests") and the list of anything not done, with the reason

Then the Lead re-tests in the browser and merges. **Make it the best part of the project.**
