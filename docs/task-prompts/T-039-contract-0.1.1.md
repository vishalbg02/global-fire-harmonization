# Task prompt: T-039 follow-up, contract 0.1.1

> Prepared for: Member 3 · Date: 2026-11-14 · Based on main @ f06cf69
> Source of truth: the Lead's comment on PR #39 (2026-11-14, "Contract 0.1.1 is merged (#41)") and `docs/DATA_CONTRACT.md` 0.1.1 additions (D-022, D-026). This prompt adds no scope beyond it. The T-039 tracker row stays open until phase 2 (T-014), and this PR does not edit the tracker.

## 1. Objective

Make the API and the app accept contract 0.1.1, so Member 2's raw-only products load without a parse error: the new reason code `NOT_HARMONIZED` is known to both, and `contract_version` `0.1.1` is the version they declare.

## 2. In scope

- `app/src/api/contract.ts`: add `NOT_HARMONIZED` to `REASON_CODES`; `CONTRACT_VERSION` becomes `0.1.1`.
- `app/src/content/reasonTexts.ts`: the Lead-approved text, "Harmonized values aren't computed yet; this shows raw satellite data only."
- `app/src/content/reasonCodes.ts`: a short map-tooltip label ("Raw data only"; not an approved text, a tooltip label like the others).
- `api/fire_api/models.py` and `api/fire_api/__init__.py`: the same enum value and version.
- Tests on both sides (SYNTHETIC data only).

## 3. Out of scope

- Wiring `harmonize_area()` into the custom-area endpoints (mentioned by the Lead on #38 for "your next PR or a small follow-up"; waiting for the Lead's choice).
- Any contract, method or tracker change. Nothing in `pipeline/` or `data/`.

## 4. Behaviour notes

- The app already treats `-raw-only` methods as "harmonization in progress". Lead review on this PR: the evidence panel must show the `NOT_HARMONIZED` text, so the "Why" section now appears in raw-only mode when the record carries reason codes (the empty "no caveats" message stays hidden).
- No value is computed; the code is read as stored.

## 5. Acceptance

- `ruff`, `pytest`, app lint, typecheck, `vitest` and build pass; results go in the PR description.
- The reason-text test (every code has text) fails if a code lacks text.
