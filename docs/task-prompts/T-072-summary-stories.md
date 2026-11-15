# Task prompt: T-072 UI summary card, featured stories and "How to read this"

> Prepared for: Member 3 · Date: 2026-11-15 · Based on main @ 2bf0df6
> Source of truth: PR #73 (assignment) and docs/TASK_TRACKER.md row T-072 ("Above-the-fold card for the selected area and month (verdict, probability, % of normal, 90% interval, a 12-month sparkline, reason text); featured quick-picks with captions from T-079 (Indonesia 2015-09, Australia 2019-12 country, Canada 2023-08, Brazil 2019-08, World 2026-10); a short dismissible 'How to read this' for first-time users"), the Lead's decision on #78 (T-080: the summary card and its sparkline with the p25 to p75 band are built in T-070; the sources lines too) and Member 2's content: `app/src/content/featured.ts` (T-079, merged, generated from the products) and `app/src/content/plainLanguage.ts` (T-076, #77). No new scope. Depends on T-070 (the layout) and T-079.

## 1. Objective

A first-time judge lands on a story, understands the verdict without scrolling, and knows how to read the colours: featured stories as one-click starting points with verified captions, and a short "How to read this" that can be dismissed and reopened.

## 2. What T-072 adds on top of T-070

- **Featured stories (chips in the row under the toolbar, built as an empty styled slot in T-070):** the five stories of `FEATURED_STORIES` (Indonesia 2015-09, Australia 2019-12 at country level, Canada 2023-08, Brazil 2019-08, World 2026-10). Clicking one selects its area and month (and zooms the map). The selected story shows under the summary card its headline, caption, the [VERIFIED] label, the source line, the query in words and the link to the report, all taken from `featured.ts` (never retyped, never recomputed; a test checks that the summary card's numbers equal the story's stored facts for the same area and month).
- **"How to read this":** a short dismissible card for first-time users (the Lead's header link opens it again), with the steps and the glossary hints of `plainLanguage.ts`; dismissal is remembered per browser (localStorage, wrapped in try/catch; the page works without it).
- **The "Black Summer" explanation** (Lead, D-031) appears with the Australia story: the cells read "cannot determine" (insufficient baseline) while the country is above normal (328%); the text is Member 2's.

## 3. Out of scope

The summary card, sparkline and source lines (T-070), the map behaviour (T-071), the payload (T-073), the phone and accessibility audit and the offline copy (T-074), rewording any text (Member 2's T-076 owns the content files).

## 4. Open questions for the Lead (defaults)

1. **First visit:** open on the first story (Indonesia 2015-09) or on the latest determinable month of the world (T-071)? Default: the world on the latest determinable month, with the stories chips visible and the "How to read this" card open once; a story is one click away.
2. **Story rule:** a story is selected when the current area and month equal it; changing the area or month clears the story caption (the numbers on screen then are not the story's). Default: yes.
3. **Where the caption goes:** a compact card under the summary card on desktop, and under the chips on the phone. Default: yes.
4. **Dismissal storage:** `localStorage` key `gfh.howto.dismissed`, no cookies, nothing sent anywhere. Default: yes.

## 5. Acceptance

- A judge understands the main verdict without scrolling; each story selects the right area and month and shows its stored numbers and label; "How to read this" dismisses and reopens; keyboard and screen-reader use works; screenshots at 1440x900, 1280x720 and 375; tests, lint, typecheck and build pass; the offline copy still opens on a story.
