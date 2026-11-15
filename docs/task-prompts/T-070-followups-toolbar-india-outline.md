# Task prompt: T-070/T-085 follow-ups: toolbar on one row, India outline above cells, fit to polygon

> Prepared for: Member 3 · Date: 2026-11-15 · Based on main (HEAD at branch creation)
> Source of truth: the Lead's comments on PR #73 (toolbar layout) and PR #88 (India outline follow-ups).

## Goal
Three small display-only fixes in the app.

## Scope
- **A. Toolbar.** With the month picker (T-087) the toolbar wraps at 1440x900 ("Draw or type an area" and "Copy link" fall under the Area box). Tidy the toolbar grid in `app/src/styles/layout.css` (markup in `App.tsx` only if needed) so it is one row at 1440x900 and wraps cleanly below. Phone layout stays as in T-070/T-074 (44 px touch targets, no horizontal scroll). `MonthSelector.tsx` is not edited.
- **B. Selection outline above the cells.** The selected-country outline is drawn under the cells, so for India only the northern piece shows. Draw it above the cell layer, like the hover outline (`MapView.tsx`).
- **C. Fit to the country polygon.** Zoom to the polygon bounds of the countries file already loaded for the hover layer, not to the cells' bounds (India: far north of Jammu and Kashmir and Ladakh was cut off). Same padding; fall back to the cell bounds if the shape is missing. World-view fit (-180,-60,180,80) and custom-area fits are unchanged. Unit tests of the pure bounds helper use SYNTHETIC polygons (including one crossing the antimeridian if the existing code handles it).

## Out of scope
`app/public/geo/`, `components/methods/`, `components/analytics/`, `MonthSelector.tsx`, data, API, methods, `docs/TASK_TRACKER.md`. PR #89 (T-084) also edits `MapView.tsx` and `App.tsx`: keep edits small and local.

## Acceptance
- Screenshots at 1440x900, 1280x720 and 375.
- India (`?area=COUNTRY:IND&month=2026-10`) at 1440x900: the full outline is visible above the cells and the far north is inside the view.
- Hover and click-select still work. `npx tsc -b`, `npm run lint`, `npx vitest run`, `npm run build` pass.

## Git
Branch `frontend/T-070-toolbar-india-outline` from the latest `main`; first commit: this prompt; draft PR; never merge; human identity, no AI attribution (D-020).
