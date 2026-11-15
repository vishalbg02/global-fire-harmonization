# T-074: responsive, accessibility and the offline copy

Date: 2026-11-15. Browser: the Chromium engine of the desktop app's browser pane (Chrome family), plus headless Google Chrome for three desktop screenshots. Chrome, Safari and Firefox on real devices are the Lead's T-081 (not run here). Real products (`synthetic: false`), contract 0.1.1, method 0.1.0.

## Method (all verified unless marked)

- **axe-core 4.10.2** injected into the page from a copy kept outside the repository (npm tarball, sha512 checked against the registry value `RE3mdQ7P...4tEI0w==`, only `axe.min.js` extracted, nothing added to the repository or `package.json`). Rules run: WCAG 2.0/2.1 A and AA, WCAG 2.2 AA (includes the 24 px target size) and axe best-practice rules.
- **Lighthouse accessibility: not run.** No Lighthouse is installed, the Lead did not approve installing one, and Chrome's built-in Lighthouse cannot be started headlessly without it. The axe result below is the automated check.
- Views: first visit (How to read this open), a country with a story (Brazil, August 2019) on each tab (Calendar, Satellites, Evidence in detail, All anomalies, Analytics), a pinned map cell, a custom area with the draw panel open, and the methods page; at 1440 px and at 375 px.

## axe results

| Moment | Violations (A, AA, 2.2 AA, best practice) |
|---|---|
| Before (main + T-070..T-073), 1440 px | `target-size` on 3 controls (two radio buttons, one checkbox, 13 px) on the Calendar tab and a custom area; 1 checkbox on Satellites; no other violation |
| Before, 375 px | the same `target-size`; and (found with a layout probe, not axe) a page 667 px wide (the screen-reader sparkline table) and 787 px wide on the methods page; 49 controls under 44 px on the first screen set |
| After, 1440 px, every view listed above | **0** |
| After, 375 px, every view listed above | **0** |

While working, two issues of my own appeared and were fixed before the final run (a focusable overlay canvas, `aria-hidden-focus`; heading levels of the draw panel, `heading-order`). axe also lists `color-contrast` as "needs review" (17 to 18 nodes on the map page) because the text sits on the map picture: the on-map overlays (`.map-legend`, `.map-hint`, `.map-mode-hint`, `.map-pinned`) use ink or `#3a3f4a`/`#566070` text on a white fill of 85 to 100 % opacity; the worst case (85 % white over black) is `#d9d9d9`, and `#3a3f4a` on it is above 7:1. That is a calculation, not an axe pass.

## Fixes (display, layout and keyboard only)

- A phone page no longer scrolls sideways at 320, 375, 640, 720 (a 1440 screen at 200 % zoom), 768, 1024, 1280 and 1440 px on every tab (probe of the page's scroll width): the sparkline table is clipped, the methods page wraps long values and addresses, the Analytics table scrolls in its own box, the toolbar is one column under 400 px. Page height at 375 px is 3.6 to 4.3 thousand px (was about 7,200 before T-070/T-072).
- Phone touch targets of 44 px for buttons, chips, tabs, the area box, the month slider, segments, the zoom buttons and the pinned-card close; 24 px checkboxes and radios everywhere. Inline links inside a sentence are left at text size (exempt in WCAG 2.5.8): "NASA FIRMS", "Methods and validation", "How this verdict is made" and "Raw hotspot points" in the source lines are 16 px high on a phone.
- Focus: `summary` and the map's zoom buttons now show the same 2 px `--focus` ring (summary had the browser default, an orange 1 px ring); tab and story-chip rings are not clipped by their scrolling rows; deck.gl's cell canvas is `inert` (it was a second, unnamed Tab stop).
- Esc closes "How to read this" (not remembered as dismissed) and the draw panel; focus returns to the button that opened them, and to the map when the pinned cell card closes.
- The draw panel's headings follow the page outline (h2, h3).

## Keyboard path (tried with real key presses unless marked "script")

Skip link (visible, focus ring 2 px blue) then Methods link, How to read this, area search, Play, Previous, slider, Next, Raw/Harmonized, "About this choice", and on: every focusable element's outline was read after focusing (all 2 px solid, blue on light, white on the navy header). Esc on How to read this and on the draw panel (focus came back to their buttons); a pinned cell and Esc on its close button (focus went to the map canvas); Right arrow on the tab bar moved Calendar to Satellites with the ring visible; combobox typing and Esc (script); month Previous/Next/Play/Pause (script, clicks). **Not possible by keyboard:** choosing a map cell (MapLibre has no cell-by-cell selection); the routes to a place are the area search, the typed box, the calendar table view and the anomaly list (known limit, T-042). Focus order follows the page source (toolbar, story chips, map, summary, tabs); on a phone the summary is shown first by CSS `order`, so the source order and the visual order differ (the order stays logical; not changed because it would restructure the T-070/T-072 layout). Not run: a screen reader (VoiceOver, NVDA); reduced motion was not toggled (the CSS and code paths exist: animations are off and Play is disabled with a note when `prefers-reduced-motion` is set; checked in code and unit tests only). Text size: sizes are in px, so browser zoom (tested to 200 %) works; a larger default font size in the browser settings is not followed.

## Offline copies (real products; nothing deployed)

| | Full copy (demo laptop) | 24-month copy (web host) |
|---|---|---|
| Command | `PRODUCTS_DIR=../data/products python -m fire_api.static_export --out <dir> --overwrite` | the same with `--latest-months 24` |
| Raw size | 1,651.5 MB, 293 months, 234 areas | 225.3 MB, 24 months (2024-12 to 2026-11), 234 areas |
| Gzipped | 473.6 MB (sum of every file gzipped) | 55.3 MB |
| Time | 912 s | 114.5 s |
| Built `dist` (static-only build) | 1.7 GB | 250 MB |

Both built with `VITE_STATIC_ONLY=1` and served with `python3 -m http.server` (the API was stopped for the full-copy test). Tested in the browser: offline notices (both; the 24-month one adds the map range), first visit, the month slider (0 to 292 for the full copy, 0 to 23 for the 24-month copy, matching the manifest), Previous/Next/Play/Pause, the story chips (in the 24-month copy Brazil, August 2019 has no map: "August 2019 (no offline map)" and the summary, calendar and charts still show), all five tabs (zero axe violations), the area search, the CSV of a preset area (fetched, HTTP 200, 308 lines; the button's file was not saved), the draw panel (the controls are disabled with "Custom areas need the live service"), How to read this. Network: only the page's own origin was requested (no API call, no external host; the GIBS imagery of PR #89 is not in this branch and nothing outside the page's origin was requested). Not tested: the 24-month copy on a real web host, the CSV download dialog, the full copy on a second machine.

## Not verified

Lighthouse; a screen reader; Safari and Firefox; a real phone and tablet (a 375 px emulated viewport was used; headless Chrome cannot go below about 500 px, so the phone screenshots come from the browser pane); reduced motion switched on in the browser; contrast on the map overlays beyond the calculation above.
