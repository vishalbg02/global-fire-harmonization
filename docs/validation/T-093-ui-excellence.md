# T-093 UI and UX excellence pass: acceptance results

> Branch `frontend/T-093-phase2` (phase 1 merged earlier as PR #101). Run 2026-11-16 on the real products (method 0.1.0, contract 0.1.1, `metadata.synthetic=false`), test API on a separate port; the demo servers were not touched. Every result below actually ran; what did not run is listed as not run.

## What phase 2 adds (brief §6)

| Brief item | Status | Where |
|---|---|---|
| Flat/Globe link sync, tested | Done: the link always says the shape (`globe=1`/`globe=0`); bare address opens the globe; old links without `globe` stay flat; 15 tests | `state/mapView.ts`, `state/mapView.test.ts` |
| Space and atmosphere | Done: MapLibre sky/atmosphere on the globe, dark ocean under imagery, plain background kept offline | `components/map/imagery.ts`, `globe.css` |
| Signal, not noise at zoom ≤ 3 | Done: quiet verdicts at 12% alpha, full by zoom 4; "Show all verdicts" (`allv=1`); display only | `components/map/signal.ts` |
| Fly-to, idle rotation, pause | Done: 1.2 s ease-out fit; one turn per 3.5 min after 8 s idle at world view; pause button remembered; all off under reduced motion | `MapView.tsx`, `globeMotion.ts` |
| Hover cell outline, slim loading line, silent flat fallback | Done | `MapView.tsx`, `mapOverlays.tsx` |
| Answer hierarchy, interval bar, reason chips, story card | Done: verdict → % of normal (Mono 40 px) → probability → interval bar (estimate, 90% interval, normal range, median) → sparkline → "Why" chips → source line → actions; duplicates removed | `components/summary/*`, `StoryCaption.tsx` |
| Sticky Details tabs, remembered tab, Analytics takeaway | Done | `ui/Tabs.tsx`, `state/tabs.ts`, `analytics/` |
| Timeline scrubber | Done: 2002–2026 strip, faint line of the area's values with gaps for nulls, provisional shading, S-NPP and NOAA-20 joins from `witnessTimeline.ts`, ARIA slider keys, Play shared with Space, T-087 picker kept | `components/timeline/*` |
| Guided tour, Help sheet, "?" explainers, Start here, shortcuts, globe hint | Done: 5-step anchored tour shown once on a bare first visit; Help sheet with the approved "How to read this"; popovers with "Learn more"; shortcuts sheet (`?`) | `components/help/*`, `content/help.ts` |
| Toasts, skeletons, plain-word errors | Done | `common/Toast.tsx`, `common/States.tsx` |
| Bottom sheet, compact dock, no overlaps | Done at ≤ 900 px: three heights, drag/flick/keyboard, timeline inside the sheet top; dock as labelled icon buttons | `layout/BottomSheet.tsx`, `dock/*` |
| "Learn more" opens the methods section | Fixed (it opened at the top before) | `methods/MethodsPage.tsx` |

## Automated checks (run 2026-11-16)

| Check | Result |
|---|---|
| vitest | **904 passed, 68 files** (main: 693 in 50) |
| typecheck (`tsc -b`) | 0 errors |
| lint (`oxlint`) | 0 warnings |
| build | passes |
| pytest `pipeline/tests api/tests` | 825 passed, 21 skipped |
| `pipeline/number_check.py` | **0 mismatches** in 6,491,894 values checked |
| Main JS bundle | 427.1 kB (main 384.0 kB): **+11.2%**, inside the 15% limit. Map chunk 29.7 kB (main 22.1 kB). CSS 63.7 kB (main 41.0 kB) |

## Accessibility: axe-core 4.13.0, WCAG 2.0/2.1/2.2 A and AA tags

The run uses a local copy of axe, injected into a test tab; nothing is added to the repository. **0 violations** on:
- Indonesia 2015-09 at 1440x900 and at 390x844
- the world 2026-10 on the globe at 1440x900 and 1280x720
- an open "?" popover
- the Help sheet
- the first visit with the tour
- the shortcuts sheet
- the methods page

Two findings along the way were fixed on this branch:
- 16 px "?" targets in the interval legend, now 24 px
- test ids on the methods page at 4.46:1 contrast, caused by an 85% opacity left over from before T-093

**Not run:** Lighthouse, because no Lighthouse runner is installed and none was added. A screen-reader pass with VoiceOver or NVDA was also not run.

## Layout measurements (getBoundingClientRect, real data)

| Check | Result |
|---|---|
| 1280x720, world 2026-10 | The answer and all actions are in the first view (Details button bottom at 710 px of 720). |
| 1280x720 and 1024x768 | Indonesia 2015-09, Canada 2023-08 and Australia 2019-12: the actions end at 655–747 px; no page scroll for the answer. |
| 1440x900 | Everything through the actions is visible. For the world 2026-10, the "About the CSV" disclosure ends 15 px below the fold (known, minor). |
| Horizontal scroll | None at 320, 375, 390, 414, 600, 768, 900, 901, 960, 1024, 1280, 1440 or 1920. |
| Overlaps | Zero between the dock, legend, credit, hints, toast, zoom and pause buttons and the sheet. Checked at 1440x900, 1280x720, 1024x768, 960x700, 768x1024, 390x844, 375x812 and 320x640. |
| Touch targets | ≥ 24 px everywhere. 44 px for the phone's primary controls (dock icons, search, sheet handle band, timeline buttons). |

## Behaviour checked in the browser

- **Tour:** shows on a bare first visit and is walked by keyboard. It doesn't return after a reload, and never shows on a link with parameters. Help reopens it.
- **Shortcuts:** ← → PageUp/PageDown Space G S / ? Esc all work. Typing in the search doesn't trigger them.
- **Link sync:** the globe, the control and the address agree on load, on toggle and after reload.
- **Fly-to:** Canada and Australia land clear of the dock and legend.
- **Signal, not noise:** quiet cells stay hoverable with correct tooltips. "Show all verdicts" draws every cell.
- **Numbers:** every printed value in the answer panel equals `/api/series` for Indonesia 2015-09, Australia 2019-12, Canada 2023-08, Brazil 2019-08, the world 2026-10 and a custom area.
- **Timeline line:** its gaps match the API's nulls (world: 2002-07 to 09 and 2026-11).
- **Reduced motion:** checked in code paths and unit tests, and in headless Chromium with reduced motion emulated (no rotation, no pause button, instant fit). Not checked in the built-in browser, which can't emulate it.

## First-time-user test (brief §8)

**Simulated, not a test with a person.** The paths below are the clicks a newcomer needs on this build; no times are claimed.

1. Indonesia, September 2015 unusual? One click: the first "Start here" question, or the story chip. The verdict, % of normal and probability are the first lines of the answer.
2. Why? The "Why" chips sit directly under the verdict; one click opens the approved sentence.
3. Canada's highest month of 2023: search "Canada" in the dock, then Details → Calendar (the 2023 row).
4. Raw against harmonized: Details → Analytics, which carries a one-line takeaway; or Layers → Raw.
5. Turn the globe and switch on Satellite view: drag the globe (the first switch shows a hint), then click Satellite view in the dock.

## Not done, or open

- **Screenshots and GIFs** of the brief §8 matrix are not committed. Checks were done live and in headless runs outside the repository.
- **Offline copy:** not rebuilt and re-opened on this branch. Imagery falls back by the same code path as before, and the offline subset is covered by unit tests.
- **Wording for the Lead to review:** the Start-here question template says "unusual" (the brief's own example). The new sentences are in `content/help.ts`, `answer.ts`, `timeline.ts`, `earth.ts` and `sheet.ts`.
- **Seen, not changed:** the phone header wraps to 93 px. The selected country has two outlines (MapLibre and deck.gl). Blue Marble shows a wedge at the North Pole on the globe.
