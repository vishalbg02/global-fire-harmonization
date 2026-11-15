# Task prompt: T-074 UI responsive, accessibility and the offline copy

> Prepared for: Member 3 · Date: 2026-11-15 · Based on main @ 2bf0df6
> Source of truth: PR #73 (assignment and audit) and docs/TASK_TRACKER.md row T-074 ("Phone 375 (the month label is cut off today), tablet, keyboard-only path, visible focus, WCAG AA contrast, automated accessibility check (axe or Lighthouse a11y >= 95); regenerate the offline copy after the UI work and test it in the browser"). The last app task: it starts when T-070 (#78), T-071 (#80) and T-072 (#82) have merged, so it checks the finished UI. No new scope.

## 1. Objective

The finished UI works on a phone, a tablet and a projector, with the keyboard only, and passes an automated accessibility check; the offline copy is regenerated from the final UI and the final products and tested in the browser.

## 2. In scope

- **Phone (375) and tablet (768):** the month label is cut off today (audit item 6); every control reachable and readable; no horizontal page scroll; the page far shorter than the 7,200 px of today (the new layout puts the summary first); touch targets of at least 44 px for the main controls; the map usable (cooperative gestures from T-071).
- **Keyboard-only path** through the whole app: skip link, toolbar, search combobox, month stepper and play/pause, map mode switch, tabs, the draw panel, the pinned cell card, "How to read this", the methods page; visible focus everywhere; no keyboard trap; Esc closes what opened.
- **Contrast and colour:** WCAG AA for the new tokens in the real components (text 4.5:1, controls and focus 3:1) with the existing `contrast.test.ts` extended to the new token file; the colour-vision tests stay green.
- **Automated accessibility check** on the main views (map page, each tab, methods page, offline copy) at 1440x900 and 375, with the findings fixed or listed; the scores and the report in the PR (open question 1).
- **Offline copy:** regenerate it from the final UI and the final products (both commands of `api/README.md`: the full copy for the demo laptop and the 24-month copy for a web host), open each in the browser with the API stopped, and test the story chips, the tabs, the search, the month stepper and play, the CSV downloads and the "How to read this" card; report sizes and times.

## 3. Out of scope

Layout and design (T-070), the map behaviour (T-071), the summary and stories (T-072), the payload (T-073), content texts (Member 2), any product value or API shape; deploying anything.

## 4. Open questions for the Lead (defaults)

1. **How the accessibility check runs.** `axe-core` as a devDependency or `npx lighthouse` would add a dependency or download tools; the approved stack (D-008) has neither. Default: run `axe-core` (MIT) injected into the page in the browser, from a copy pinned by version and checksum that I download once into a scratch folder (not added to the repository), on each view, and report the violations and passes; and run Lighthouse's accessibility category only if Chrome is available here. No new repository dependency. Do you approve, or do you want a pinned devDependency recorded in the decision log?
2. **Target.** The row says a11y >= 95. Default: zero axe violations of level A and AA on the main views, and a Lighthouse accessibility score of 95 or more if it can be run; anything left is listed with its cause.
3. **Offline copy sizes.** The full copy is about 474 MB gzipped and is for the demo laptop only; the 24-month copy (about 55 MB) is for a web host. Default: regenerate both, test both, deploy neither.
4. **Browsers.** The Lead's T-081 covers Chrome, Safari and Firefox; I test in the browser pane available here (a Chromium engine) and say so. Default: yes.

## 5. Acceptance

- Screenshots at 375, 768, 1280x720 and 1440x900 of the finished UI; the month label no longer cut off; the keyboard-only path documented as a checklist in the PR with what was tried; the accessibility scores and report; the offline copy regenerated and tested (sizes and times reported); tests, lint, typecheck and build pass.
