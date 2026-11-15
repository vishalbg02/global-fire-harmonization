# Task prompt: T-085 India's official boundary on the map

> Prepared for: Member 3 · Date: 2026-11-15
> Source of truth: the Lead's instruction in the comment on PR #73.

## 1. Goal
The map outlines India with the Natural Earth de facto line, which stops near 35.5 N. At an event in India the map must show India's official boundary, with Jammu and Kashmir, Ladakh and Aksai Chin inside India.

## 2. Scope
- Replace the map's country-outline file with Natural Earth's "Admin 0 countries, India point of view" (1:10m), simplified to about the size of the current file (838 KB), keeping the properties the app reads (`ISO_A3_EH`, `NAME`, `ADMIN`).
- Keep country ids stable (ADM0_A3 and `ISO_A3_EH` sets compared with the old file, differences reported); keep hover, click and area selection working.
- Rename the file if the old name (`110m`) would mislead, and update every reference.
- Credit, source URL, date, SHA-256, simplification and licence in `docs/DATA_SOURCES.md`; a one-line limitation in `docs/RISKS_AND_LIMITATIONS.md`.

## 3. Out of scope
- Any product value, verdict, threshold or data contract change.
- Which country a grid cell is attributed to (Member 2, T-086).
- Other disputed boundaries beyond what the Natural Earth India file already draws.
- New dependencies (mapshaper is used once with `npx`, outside the repository).

## 4. Constraints
The one permitted download is the Natural Earth file named above. Untrusted data is kept outside the repository and checked before use. No AI attribution anywhere (D-020).

## 5. Acceptance
- India's feature reaches about 37.05 N and contains Jammu and Kashmir, Ladakh and Aksai Chin; Pakistan and China outlines are consistent with it.
- No country is lost or renamed without being reported; hover and click select India (`IND`) and the other countries as before.
- App tests, lint, typecheck and build pass; numbers reported from real runs.
- Screenshots at 1440x900 and 375 wide in the PR description or comments.
