# Task prompt: T-087 A month picker that is easy to use

> Prepared for: Member 2 · Date: 2026-11-15 · Based on main (HEAD at branch creation)
> Source of truth: the Lead's comment on PR #74 (2026-11-15 06:08): "New, now: T-087, a month picker that is easy to use".

## 1. Context
The month slider covers 293 months (2002-07 to 2026-11) on a control about 140 px wide, so one pixel is about two months. Reaching a given month (for example December 2019) is hard.

## 2. Objective
Keep the slider for scrubbing and add the controls that make any month easy to reach, in a clean instrument style, without changing what the map shows.

## 3. Assigned responsibility
T-087 / P0 · Owner: Member 2 · Reviewer and merger: Member 1 · Member 3 does not touch `MonthSelector.tsx` meanwhile. Target about 12:00 IST.

## 4. Files
- Modify: `app/src/components/map/MonthSelector.tsx` (props and exports stay compatible: `months`, `value`, `onChange`)
- Create: `app/src/components/map/monthPicker.ts` (pure logic), `monthPicker.test.ts`, `MonthPicker.tsx` (the popover), `monthPicker.css`, `monthPicker.test.tsx`, `app/src/content/monthPicker.ts` (texts)
- Do not touch: other Member 3 files, `styles/tokens.css` (read only), the API, products

## 5. Requirements (from the Lead)
1. Keep the slider; add **year ticks** and a **larger thumb and hit area** (at least 24 px).
2. A **year/month picker** next to the month label: a year select (2002 to the latest) and **12 month buttons per year**; months outside the record are disabled, provisional months are marked; **any month takes at most 2 clicks** (open the picker, press the month: the picker lists every year, scrolled to the current one, and the year select jumps to a year).
3. **Previous and next month** (existing) plus **previous and next year**.
4. Keyboard: arrows move months, PageUp and PageDown years, Home and End the first and last month; typing `2019-12` works (a text field in the picker; invalid input says what is valid).
5. Play and Pause and the `month=` link behaviour are unchanged; any manual choice pauses playback.
6. Existing tokens (`styles/tokens.css`); no gradients, no shadows; accessible names; touch targets as large as the toolbar allows on a phone.
7. Real data only: months come from the metadata through the existing props; no fixtures in production code.

## 6. Tests
Vitest for the pure logic (clamping to the first and last month, provisional marking, parsing of `2019-12` and rejected input, keyboard actions, at most 2 clicks to reach any month) and render tests; `npm test`, `npm run typecheck`, `npm run lint`, `npm run build`; a browser check on the real API at 1440x900 and 375.

## 7. Git
Branch `frontend/T-087-month-picker` from the latest `main`; first commit: this prompt; PR with the template, screenshots checked at 1440x900 and 375 (not committed), the real-data statement; never merge; human identity, no AI attribution (D-020).
