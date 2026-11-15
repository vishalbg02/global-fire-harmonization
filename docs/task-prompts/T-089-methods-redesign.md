# Task prompt: T-089 Methods and validation page redesign

> Prepared for: Member 2 · Date: 2026-11-15 · Based on main (HEAD at branch creation)
> Source of truth: the Lead's comment on PR #74 ("New batch for Member 2: T-089, T-090, T-091").

## Task
The judges read the Methods and validation page to check the project's honesty. Make it the clearest page in the app, in `app/src/components/methods/` only (plus content strings in `app/src/content/` and tests).

## Requirements (the Lead's list)
1. "In plain words" (`IN_PLAIN_WORDS`, approved, not mounted yet) at the top.
2. A results overview before the details: the counts from the stored results (never typed) and one line per test family (A1, A2, B1, B2, B3, C1, CTRL, D1, D2, E1, S1) with its status and a one-sentence meaning taken from the stored fields; failures as prominent as passes; each line links to its detail.
3. Filter chips (All / Pass / Fail / Inconclusive, plus Not run when present) and a collapsible detail per test.
4. Readable measured values: a label made from the stored key; values exactly as stored (no rounding).
5. An on-page table of contents; the T-070 tokens and type (IBM Plex, thin rules, no shadows); works at 375.
6. Acceptance: a judge finds every FAIL and why in under 30 seconds. Screenshots at 1440x900 and 375.

## Decisions fixed before building
- Family key = the part of `test_id` before the first hyphen. Family status = the family-level entry (`test_id` equal to the key, or `<key>-FAMILY`) when the file has one; otherwise the worst status of its entries (FAIL, then INCONCLUSIVE, then NOT_RUN, then PASS). The rule is stated on the page and the entry counts of every family are shown beside its status, so a pass never hides a failing entry.
- The meaning line is the stored title of the family-level entry (or of the first entry). No new claims.
- Failing and inconclusive details are open by default; passing ones are collapsed.
- Existing anchors keep working (`reason-<CODE>`, section ids, `method-<id>`), and the plain section ids that other components link to (`#baseline-verdicts`, `#sources`) resolve to an element.

## Not changed
Method, thresholds, products, the stored statuses and their wording. The results are read through the existing API client.

## Git
Branch `frontend/T-089-methods-redesign` from the latest `main`; first commit: this prompt; PR with the template and the real-data statement; never merge; human identity, no AI attribution (D-020).
