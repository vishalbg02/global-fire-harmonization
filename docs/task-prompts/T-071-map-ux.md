# Task prompt: T-071 UI: map experience

> Prepared for: Member 3 · Date: 2026-11-15 · Based on main @ 8408758
> Source of truth: PR #73 (assignment of T-070 to T-074 and the Lead's audit of 2026-11-15) and docs/TASK_TRACKER.md row T-071 ("Open on the latest determinable month; page scroll never zooms the map (zoom with Ctrl/Cmd + scroll or the buttons, with a hint); legend on the map; lighter cell outlines; NO_DETECTED_ACTIVITY clearly different from BELOW_NORMAL (colour-blind safe, icon kept); loading state; clicked cell info stays pinned"). Depends on T-070 (the layout); it is built against the current App.tsx with minimal edits there and rebased on T-070 when that merges. Display only: no product value, verdict rule, API shape or contract change.

## 1. Objective

The map is the hero and behaves like one: it opens on a month that shows something, the page can be scrolled over it, the legend is on it, the cells read clearly, loading is visible, and a clicked cell stays readable.

## 2. What the audit found that T-071 answers (browser test of main, 2026-11-15, real products)

1. The app opens on 2026-11, where every cell is `CANNOT_DETERMINE` (outage and provisional): the whole world is grey.
3. Scrolling the page over the map zooms the map.
4. Dense dark cell outlines (the 1 px dark stroke makes a mesh).
5. `NO_DETECTED_ACTIVITY` (pale blue) is easy to confuse with `BELOW_NORMAL` (blue).
(Also from the Lead's review: the legend sits in the sidebar, far from the map; the reason text must be visible for a clicked cell.)

## 3. In scope

1. **Initial month.** Pure function: from the GLOBAL series, the latest month whose record has a non-null `estimate` and no `OUTAGE` reason code; fall back to `meta.latest_month`. A month in the link wins. No API change (existing `GET /api/series?entity_type=GLOBAL&entity_id=GLOBAL`). One small hook in a new file and one or two lines in `App.tsx`.
2. **Scroll never zooms.** MapLibre `cooperativeGestures` (Ctrl/Cmd + scroll zooms, two-finger touch pan), a short hint on the map, the +/- buttons and keyboard zoom unchanged.
3. **Legend on the map.** An overlay at the bottom left of the map for the verdict and activity layers (same content and cues as today, including the "No data (dark outline)" swatch and the verdict icons), collapsible on small widths. The sidebar legend is removed only if that is a one-line change in `App.tsx`.
4. **Lighter cell outlines.** A thin, low-alpha stroke whose width follows the zoom (none at world zoom); the selected-cell blue outline and the "no data" dark outline stay.
5. **`NO_DETECTED_ACTIVITY` tone.** A new colour-blind-safe tone, apart from the other four verdict colours and visible on the land colour; the open-circle icon stays. `colorVision.test.tsx`, the legend and the risk row T18 follow; thresholds are not weakened.
6. **Loading state.** A visible, accessible indicator on the map while the month's cells load; the existing error and empty states stay.
7. **Pinned cell card.** Clicking a cell opens a card on the map with the cell details (the full approved reason sentences of `reasonTexts.ts` included) that stays until dismissed (button or Esc) or another cell is clicked. The hover tooltip stays.

Files: `app/src/components/map/*`, `app/src/state/*`, one new hook file, `app/src/content/verdicts.ts` (colour only), tests, `app/README.md` and `docs/RISKS_AND_LIMITATIONS.md` (T18).

## 4. Out of scope

Header, toolbar, tabs and the layout (T-070); `app/src/content/*.ts` texts other than the colour in `verdicts.ts` (Member 2, T-076); the summary card, stories and how-to (T-072); the payload (T-073); phone and accessibility audit (T-074); any product value, verdict rule or API shape.

## 5. Open questions for the Lead, with defaults

1. **"Determinable" rule.** Default: non-null `estimate` and no `OUTAGE` code in the GLOBAL record (a provisional month with an estimate still counts). Alternative: also exclude `PROVISIONAL_NRT`.
2. **Zoom gesture.** Default: Ctrl/Cmd + scroll (MapLibre cooperative gestures), with the hint "Use Ctrl + scroll to zoom the map" (Cmd on macOS is handled by the same gesture).
3. **Hint text location.** `app/src/content/ui.ts` does not exist on main (T-070 plans it); default: a small constant in the map folder, moved to `ui.ts` by T-070's rebase if Member 2 wants it there.
4. **Sidebar legend.** Default: removed from the sidebar if it is a one-line change, otherwise kept and reported.
5. **Cell outlines.** Default: no outline below zoom 3, then about 0.5 px at alpha 35, rising to 1 px at close zoom.

## 6. Acceptance

- The app opens on the latest determinable month (2026-10 on the real products, to be confirmed by the check) unless the link names a month.
- Wheel-scrolling over the map scrolls the page; Ctrl + wheel and the buttons zoom.
- The legend is on the map; outlines are light; `NO_DETECTED_ACTIVITY` is clearly different from `BELOW_NORMAL` with measured CIEDE2000 values in all four vision modes; loading is visible; a clicked cell stays pinned and Esc closes it, with the reason text visible.
- Before and after screenshots at 1440x900; lint, typecheck, tests, build and audit pass.
