# Task prompt: T-041 Methods and validation results page

> Prepared for: Member 3 · Date: 2026-11-14 · Based on main @ 1b4b252
> Source of truth: docs/TASK_TRACKER.md row T-041 and the Lead's assignment in PR #38 ("render `validation_results.json` as-is plus the method summary from `docs/SCIENTIFIC_METHODOLOGY.md`. Never show a test as passed unless the file says so. Add the reason-code texts from T-036 and the D-009 grid evidence"). `docs/prompts/MEMBER_3_APPLICATION_PROMPT.md` §15. This prompt adds no scope beyond them. The Lead marks the tracker row; this task does not edit it.

## 1. Objective

A "Methods and validation" page in the app: the method in plain language, the validation results exactly as `GET /api/validation` serves them (PASS, FAIL, INCONCLUSIVE, NOT_RUN), the reason codes with their approved texts, the grid evidence (D-009), and the FIRMS acknowledgement and references. Failures are as prominent as passes; nothing is shown as passed unless the file says so; nothing is computed.

## 2. Dependencies and current data

T-020 and the API (T-034) are merged. The real `data/products/validation_results.json` today has `"tests": []` and `synthetic: false`, so the page must say "no validation test has been run yet", which is not the same as every test being NOT_RUN. The contract allows four statuses (§6 of DATA_CONTRACT.md); the page handles all four and an empty list.

## 3. In scope

- API client function and strict parser for `/api/validation` (unknown status or missing field is a visible error, like the other endpoints).
- The page: method summary, validation results, reason codes (all 11 including NOT_HARMONIZED, from `reasonTexts.ts`), D-009 grid evidence, acknowledgement and references.
- A link to the page in the app header and "learn more" links from the evidence panel's reason codes (MEMBER_3 prompt §10 item 5 and 7).
- Tests with SYNTHETIC data only (all four statuses, empty list, failures not reordered, synthetic label, 503 message).
- `app/README.md` and `docs/RISKS_AND_LIMITATIONS.md` if a limit appears.

## 4. Out of scope

- Writing validation results, changing thresholds or the method (Member 2 / the Lead). Nothing in `pipeline/`, `data/` or the API.
- Static fallback (T-043), performance and accessibility pass (T-042, though the page will be keyboard-usable and not colour-only).

## 5. Open questions, with defaults

1. **Where the page lives.** The app is one page with no router. Default: a "Methods and validation" view switched by a header link and kept in the URL (`?page=methods`), no router library, no new dependency; the map view keeps its state when you return.
2. **Method text.** The prompt says Member 2 supplies the content and the Lead approves it. Default: I draft plain-language text into `app/src/content/methods.ts` only from `docs/SCIENTIFIC_METHODOLOGY.md` (what a hotspot is, why sensors differ, witnesses and calibration, combination and uncertainty, baseline and verdicts, limitations), keeping its labels (APPROVED, PROPOSED, VERIFIED, LIMITATION) visible and inventing nothing; the Lead approves the wording in this PR. Is Member 2 expected to supply it instead?
3. **Empty validation file.** Default: with `tests: []`, show "No validation test has been run yet. Results, including failures, will appear here" with the file's `generated_at`, `method_version` and `synthetic`. I do not list the planned tests from `VALIDATION_PLAN.md` as rows, to avoid showing hard-coded tests that are not in the file; the page links the plan by name only.
4. **Result rows.** Default: in file order (never reordered), each with the status as text plus an icon (not colour alone), title, case, criterion, threshold, measured values (null shown as "not measured") and notes; a count of each status at the top; FAIL and INCONCLUSIVE styled at least as strongly as PASS.
5. **Synthetic data.** Default: when `synthetic` is true, a SYNTHETIC banner on the results, as elsewhere.
6. **D-009 grid evidence.** Default: the four-row table from `docs/DECISION_LOG.md` (D-009) as static content with its source cited and the known consequences in a sentence.
7. **Acknowledgement and references.** Default: the FIRMS acknowledgement from `/api/meta` `citation` (not retyped), and the references of `SCIENTIFIC_METHODOLOGY.md` §9 as written.
8. **"Learn more" links.** Default: each reason code in the evidence panel links to its anchor on the methods page.

## 6. Acceptance

- All four statuses, an empty list, a synthetic file and a `503` render correctly in tests; a test fails if the page shows PASS for anything the file does not mark PASS.
- Lint, typecheck, tests and build pass; screenshots of the page on real data (empty results) and of a synthetic file with all four statuses go with the PR, as usual.
