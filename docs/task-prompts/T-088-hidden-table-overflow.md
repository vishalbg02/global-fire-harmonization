# Task prompt: T-088 Hotfix: horizontal page scroll at 1440 wide

> Prepared for: Member 2 · Date: 2026-11-15 · Based on main (HEAD at branch creation)
> Source of truth: the Lead's comment on PR #74 ("URGENT hotfix, now: horizontal page scroll at 1440 wide (T-088)").

## Task
At 1440x900 `document.documentElement.scrollWidth` is 1693 against a 1440 viewport. Cause: the sparkline's hidden data table (`table.visually-hidden` in the summary card) spans x 1032 to 1693, because a `<table>` ignores the `width: 1px` of `.visually-hidden` (`app/src/index.css`, two duplicate rules around lines 577 and 679). Make `.visually-hidden` robust for tables (CSS only), remove the duplicate rule, add a test, and check in the browser that `scrollWidth === innerWidth` at 1440, 1280, 768 and 375 on the summary card, calendar, satellites and analytics tabs.

## Files
Modify: `app/src/index.css` only (one `.visually-hidden` rule, a `table.visually-hidden` rule). Add a test (`app/src/styles` or next to the CSS tests). No component, API, product or method change.

## Requirements
One `.visually-hidden` rule with `position: absolute; width: 1px; height: 1px; margin: -1px; padding: 0; border: 0; overflow: hidden; clip: rect(0 0 0 0); clip-path: inset(50%); white-space: nowrap;` and `table.visually-hidden { display: block; }`. The text stays available to screen readers.

## Git
Branch `frontend/T-088-hidden-table-overflow` from the latest `main`; first commit: this prompt; PR with the template, real-data statement ("Real data: `metadata.synthetic=false`, no synthetic banner shown, no fixture imported outside tests"); never merge; human identity, no AI attribution (D-020).
