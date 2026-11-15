# Task prompt: T-076 Plain-language content pass

> Prepared for: Member 2 · Date: 2026-11-15 · Based on main (HEAD at branch creation)
> Source of truth: `docs/TASK_TRACKER.md` row T-076 (PR #74) and the Lead's audit of 2026-11-15.

## 1. Project context
A judge reads the app cold. The Lead's audit found an evidence panel for Australia 2019-12 that says "Satellites disagree; uncertainty widened (disagreement scale 1.78)" and, below it, "No caveats are recorded for this month". The `WITNESS_DISAGREEMENT` code needs a scale above 2, so the two texts read as a contradiction. The UI is being rebuilt by Member 3 (T-070 to T-074), which needs the texts for "How to read this" and short glossary hints.

## 2. Task objective
Plain-language texts for the app that claim nothing beyond the method, and the contradiction fixed.

## 3. Assigned responsibility
Task T-076 / P0 · Owner: Member 2 · Reviewer and merger: Member 1 · Keys agreed with Member 3 (comment on the PR).

## 4. Relevant files and directories
- Read: `app/src/content/*.ts`, `app/src/components/evidence/EvidenceBody.tsx` and its test, `docs/DECISION_LOG.md` (D-028, D-031), `docs/NUMBER_INVENTORY.md`
- Create: `app/src/content/plainLanguage.ts` (How to read this, glossary hints, an "in plain words" summary of the method) and `app/src/content/plainLanguage.test.ts`, `app/src/content/evidenceText.ts` (the disagreement note and the no-caveats text)
- Modify, minimally: `app/src/components/evidence/EvidenceBody.tsx` (use the two content strings; no layout or behaviour change) and `evidence.test.tsx` (the new strings)
- Do not touch: reason-code texts approved by the Lead on PR #28 (`reasonTexts.ts`, tested as the approved wording) unless this PR shows a concrete reader problem; methods text (approved wording, status labels); `api/`; products

## 5. Approved technologies
TypeScript, vitest, the existing app toolchain. No new dependency.

## 6. Architecture and data contract
No contract change. Texts only.

## 7. Inputs
The method as approved: D-028 (baseline = same calendar month 2003 to 2022, normal range = 25th to 75th percentile, % of normal = estimate over the baseline median, verdict probabilities at 80%), D-031, `docs/NUMBER_INVENTORY.md`.

## 8. Expected outputs
The content file and tests; the evidence panel no longer contradicts itself; a list of what was changed and why in the PR.

## 9. Implementation requirements
1. **Contradiction:** the satellite-disagreement note for a scale above 1 and up to 2 says the interval was widened as a routine adjustment and is **not** a caveat flag; the "Why" text for an empty list says no caveat flags are recorded. A scale above 2 keeps showing the stored `WITNESS_DISAGREEMENT` reason as before.
2. **How to read this** (for the dismissible card of T-072): five or six short steps, from picking a place and month to reading a verdict, the percentage, the interval, "cannot determine" and what the unit is.
3. **Glossary hints:** one or two sentences each for: fire-active cell-day, Aqua-equivalent, harmonized estimate, normal range, % of normal, 90% interval, verdict, cannot determine, provisional, raw (unharmonized) view.
4. **In plain words** (summary of the method for the top of the methods page): what the tool does and does not do, in a few short paragraphs, with no formula.
5. Every statement is a restatement of the approved method or of the products; no cause, no forecast, no claim about fires or burned area (hotspots are not fire counts or burned area). No jargon without a hint; no "witness", "stratum" or "harmonize" without explanation.
6. Tests: every glossary term and step is non-empty, forbidden phrases are absent ("number of fires", "burned area" only in a negation, "anomaly" as a synonym of "above normal"), and the evidence panel shows the note and the no-caveats text consistently.

## 10. Constraints: do not modify
Method, thresholds, products, D-028, D-031, the approved reason texts, the layout of the app.

## 11. Acceptance criteria
Texts reviewed by the Lead; no claim beyond the method; app tests pass; typecheck and lint pass.

## 12. Required tests
`npm test` (vitest), `npm run typecheck`, `npm run lint` in `app/`.

## 13. Documentation updates
None beyond the PR description (the tracker row is in PR #74).

## 14. Git branch and PR instructions
Branch `content/T-076-plain-language` from the latest `main`; first commit: this prompt; open a PR with the template; never merge; human Git identity, no AI attribution (D-020).

## 15. Out-of-scope or blocking issues
Wiring "How to read this" and the glossary into the UI is Member 3's (T-072, T-070); this PR supplies the texts and the exact keys.
