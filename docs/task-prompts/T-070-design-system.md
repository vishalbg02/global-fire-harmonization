# Task prompt: T-070 UI design system and layout

> Prepared for: Member 3 · Date: 2026-11-15 · Based on main @ 8408758
> Source of truth: PR #73 (assignment of T-070 to T-074 and the Lead's audit of 2026-11-15) and docs/TASK_TRACKER.md row T-070 ("Header with name and one-line purpose; CSS design tokens; consistent buttons and inputs; map as the hero with a right panel whose top shows the selected area's summary; controls grouped in one toolbar; calendar, evidence and chart reorganised so the key verdict is above the fold. Post a mock for the Lead's approval (T-080) before the full build"). Merge target about 12:30 IST. This prompt adds no scope beyond these. Display and layout only: no product value, verdict rule or contract change.

## 1. Objective

The app looks and reads like a finished product: a clear header, one visual system, and a layout where a judge sees the verdict for the selected area and month without scrolling. Nothing that is shown today is lost.

## 2. What the audit found that T-070 answers (browser test of main, 2026-11-15)

- The evidence panel with the verdict starts about 3,700 px down (four screens at 1440x900); the anomaly list about 1,350 px down in a long side column.
- Browser-default buttons, inputs and headings, no header or hierarchy.
- (T-071 owns the map behaviour, T-072 the summary card content and stories, T-073 the payload, T-074 the phone and accessibility checks; T-070 builds the layout and the system they sit in.)

## 3. The mock (for T-080, the Lead's approval before the build)

A static layout mock, using the real products' Indonesia September 2015 values and the app's own map image (a real screenshot; T-071 lightens the outlines), is in `docs/task-prompts/assets/T-070/layout-mock.html` (open it from a local server, `python3 -m http.server` in that folder; it reflows by width). Screenshots at 1440x900 (top and scrolled), 1280x720 (projector) and 375 are attached to the PR.

**Design system (tokens in one place, `app/src/styles/tokens.css`):**
- Colour: ink #14181f, muted #566070, page #f3f5f9, surface #fff, border #d5dbe5, brand navy #12233f (header, selected states), accent vermillion #d55e00 (primary action, the "above normal" colour), focus #0050c8. Verdict colours unchanged (above #d55e00, below #0072b2, within #999999, cannot determine #cccccc; "no detected activity" stays the pale blue of #59 with its dashed outline and open circle).
- Type: system font stack (no web font, so the offline copy and the venue network are unaffected); scale 12, 14, 16, 20, 28, 40 px, one weight pair (400 and 700).
- Space and shape: 4, 8, 12, 16, 24, 32 px; radius 10 px for cards and 8 px for controls; one soft shadow.
- Components: primary and secondary buttons, segmented control (Raw or Harmonized, Verdict or Activity), search input, month stepper, chips (featured stories), cards, tabs, status badge (verdict), notice bars (SYNTHETIC, Offline copy), all with one visible focus style.

**Layout (desktop 1440x900 and projector 1280x720):**
1. A slim navy header: name, one line of purpose, and "Methods and validation" and "How to read this" at the right (the second one is the entry of T-072).
2. One toolbar: area search, month stepper, Data shown, Map shows, and a single "Draw or type an area" menu (the rectangle and polygon forms, today's long sidebar section, move inside it with unchanged behaviour). The CSV download moves to the summary card.
3. A row of featured-story chips (content and captions from T-072 and T-079; T-070 builds the empty, styled slot).
4. The hero: the map (about two thirds of the width, legend on the map) and a right column with the **summary card** on top (area and month, verdict badge, probability, big "% of normal", estimate and 90% interval, satellites used, reason text; T-072 adds the sparkline) and the "Biggest anomalies" list below it.
5. Below, one tabbed card: **Calendar**, **Satellites** (the chart and the satellite timeline), **Evidence in detail** (the full evidence panel as today), **All anomalies** (the full ranking with the Countries and Continents tabs).
6. The notices (SYNTHETIC, Offline copy, raw-only) stay above the header or toolbar as today.

**Phone (375):** header with the two links, the story chips, then the summary card first, then the toolbar (area, month, the two segmented controls, the menu), then the map with its legend, the anomaly list and the tabs (the mock shows this order).

## 4. In scope

`app/src/styles/*`, `App.tsx` layout and its panels' wrappers, new small layout components (header, toolbar, summary card shell, tabs), CSS tokens replacing the colour literals of `index.css`, tests, `app/README.md`, screenshots at 1440x900, 1280x720 and 375.

## 5. Out of scope

Map behaviour and colours (T-071), the sparkline, stories and the "How to read this" content (T-072), the payload (T-073), phone accessibility audit and the offline copy (T-074), any text in `app/src/content/*.ts` that belongs to Member 2's T-076 (new layout strings go in one new file, see question 5), any product value or API shape.

## 6. Open questions for the Lead (answers needed for the build)

1. **Design direction (T-080):** do you approve the mock (navy header, vermillion accent, light theme only, system fonts, cards on a light page)? Default: approved as shown. Say what to change.
2. **Split with T-072:** T-070 builds the summary card with the data the evidence panel already has (verdict, probability, % of normal, estimate, interval, satellites, reason text); T-072 adds the sparkline, the stories and the how-to. Default: yes.
3. **"Draw or type an area" menu:** the rectangle and polygon controls move into one popover or panel opened from the toolbar, with the same fields, messages and behaviour. Default: yes (nothing removed, the keyboard route stays the text boxes).
4. **Tabs:** the calendar, satellites, evidence in detail and the full anomaly list in one tabbed card (the summary card and the top five anomalies stay always visible). Default: yes; the selected tab is kept in the link (`tab=`) so a view can be shared.
5. **New layout text:** the header tagline, tab names, toolbar labels and menu names go in one new file `app/src/content/ui.ts`, so Member 2 can reword them in T-076 without touching components. Default: yes; Member 2 agrees the keys on this PR.
6. **Schedule:** to merge by about 12:30 IST I will build with parallel agents only for independent files, and rebase T-071 to T-074 on this PR once it merges.

## 7. Acceptance

- Screenshots at 1440x900, 1280x720 and 375 show the verdict above the fold; nothing that was shown is lost (a checklist of every panel and control of today's app with where it now lives is in the PR); tests, lint, typecheck and build pass; the offline copy and the keyboard path still work.
