# T-078: final number check on the finished UI, browser pass

> Member 2 · 2026-11-15 · `main` @ 701c3a7 (T-070 to T-074, T-083 to T-085, T-087 to T-089 merged), products T-014 plus T-086 (`cells.parquet` SHA-256 `decd81e6...`, `entity_month.parquet` `1d8bf0bf...`), method 0.1.0. Real API on the real products, real app (Vite dev server of this branch), built-in browser (Chromium engine) at 1440x900. **This is the browser pass and the inventory update; the function and API checker (`python pipeline/number_check.py`) is run and reported separately by the owner of T-078.** Nothing in the app, the products or the checker was changed.

## 1. Method

1. `docs/validation/T-078/expected.py` computes, from `data/products` with DuckDB and the JavaScript rounding rules of `docs/NUMBER_INVENTORY.md` (emulated by `pipeline/number_check.py`), what the finished UI should show for the five featured cases: Indonesia 2015-09, Australia 2019-12, Canada 2023-08, Brazil 2019-08 and the world 2026-10. It writes a scratch file under `app/public/_t078/` (served by Vite, deleted afterwards, never committed).
2. `docs/validation/T-078/compare.js` runs in the real app on each case's link. It reads the page and compares: the summary card, the sparkline's hidden table, the story caption (against `app/src/content/featured.ts`, and `featured.ts` facts against the stored values), and the Analytics tab (annual-sum table, season-profile table, rank text, coverage).
3. The methods page, the month picker, the map source line and the imagery day selector were read from the page and compared with `/api/validation`, `/api/meta` and the products.

## 2. Results

| Area | Checks | Mismatches |
|---|---|---|
| Indonesia 2015-09 (summary card, sparkline, story, Analytics) | 28 | 0 |
| Australia 2019-12 | 28 | 0 |
| Canada 2023-08 | 28 | 0 |
| Brazil 2019-08 | 28 | 0 |
| World 2026-10 | 27 | **1** (a label, see 3.1) |
| **Total, five cases** | **139** | **1** |
| Methods page | 6 | 0 |
| Month picker and scrubber | 6 | 0 |
| Map source line, imagery day selector | 5 | 0 |

**What each case check covers** (28 checks): title; verdict label; probability sentence; % of normal (`Math.round`); estimate (one decimal); 90% interval; satellites; number of reason lines and the "no caveat flags" text; data level text; provisional notice; the 12 rows of the sparkline table (month, estimate, normal range); the story caption (headline, text, "[VERIFIED]" label, facts equal the stored full-precision values, the caption starts with the rounded % of normal); the annual-sum table (every year: months used, raw sum, harmonized sum, "(partial)"); the season-profile table (12 months: 25th, median, 75th, selected year); the rank text (first line, ties, missing years, provisional note); coverage (the world figure, or the world-only message for a country); the "Sum of monthly estimates; intervals not combined" note; no "SYNTHETIC" text on the page.

**Values (stored, shown):**

| Case | Verdict | % of normal | Estimate | 90% interval | Rank |
|---|---|---|---|---|---|
| Indonesia 2015-09 | Above normal | 265% | 19068.7 | 17320.2 to 20817.2 | 1st highest September (24 years with an estimate) |
| Australia 2019-12 | Above normal | 328% | 11762.1 | 10175.1 to 13349.1 | 1st highest December (24 years) |
| Canada 2023-08 | Above normal | 1024% | 13660.5 | 12291.4 to 15029.7 | 1st highest August (24 years) |
| Brazil 2019-08 | Within normal | 114% | 29763.4 | 27391.3 to 32135.5 | 9th highest August (24 years) |
| World 2026-10 | Cannot determine | 91% | 122018.9 | 112066.9 to 131970.9 | 19th highest October (25 years) |

World coverage (the one exact coverage figure): "59% of 56,238 cells have a determinable verdict" (determinable = any verdict except CANNOT_DETERMINE; 22,790 of 56,238 cells are CANNOT_DETERMINE, from `cell_month_harmonized.parquet` for 2026-10). For a country the Analytics tab shows "Coverage for this area needs the cell-to-country link; shown for the world only." and no figure (PR #94 is not merged).

**Methods page** (stored file: 38 entries): the page shows PASS 18, FAIL 18, INCONCLUSIVE 2 (chips "All (38)", "FAIL (18)", "INCONCLUSIVE (2)", "PASS (18)"), equal to a tally of `/api/validation` and of the file; every one of the 18 FAIL ids is on the page; the "no test has been run" message is absent; `D1-REGIONS` `coverage_90` is shown as stored (`0.8178717598908595`); the family lines read A1 FAIL, A2 FAIL, B1 PASS, B2 FAIL, B3 PASS, C1 PASS, CTRL FAIL, D1 PASS (pooled) with `D1-NIGHT` and `D1-REGIONS-EACH` as their own FAIL lines, D2 PASS, E1 PASS, S1 FAIL.

**Month picker and scrubber:** the scrubber runs 0 to 292 (293 months), 2015-09 sits at 158 (13 years and 2 months after 2002-07); the picker lists 25 years (2002 to 2026), 300 month buttons of which 293 are enabled, equal to the 293 stored months; the 7 disabled are January to June 2002 and December 2026; exactly 4 buttons carry "provisional" (2026-08 to 2026-11, equal to `metadata.provisional_months`).

**Map source line:** "Source: NASA FIRMS active-fire products, standard (SP) MYD14, MOD14, VNP14IMG, VJ114IMG and near-real-time (NRT) MCD14DL, VNP14IMGT, VJ114IMGT; 0.5° grid; method 0.1.0." The product names equal `SP_DOIS` and `NRT_DOIS` of `api/fire_api/export.py`; "0.5° grid" equals `metadata.grid.analysis_deg`; "method 0.1.0" equals `metadata.method_version`; no date is written.

**Imagery day selector:** for 2002-07 the days offered run from 4 to 31 (first Aqua imagery day 2002-07-04, `docs/DATA_SOURCES.md` section 9) and the default is 15; for 2015-09 the 30 days of September are offered.

**India outline (T-085):** the file `ne_admin_0_countries_india_pov.geojson` reaches 37.054 degrees N for India (the old file 35.494); no number is displayed. Checked in PR #88.

## 3. Findings

### 3.1 One label differs: the world is "World" in the card and "Global" elsewhere
For the world the summary card title reads **"World, October 2026"** while the stored `entity_name` is **"Global"** and the story chip, the story headline ("Global, October 2026: cannot determine") and `featured.ts` say "Global". This is a wording difference, not a number; no value differs. Decision for the Lead and Member 3: one name for the world everywhere (the card's "World" is the app's own label for the `GLOBAL` entity, the stored name is "Global"). **Not changed here.**

### 3.2 Notes (no mismatch)
- **Computed by the app, as the inventory says:** the annual sums (sums of the stored monthly values over the months that have an estimate), the rank (1 plus the number of years with a larger estimate), the coverage share, the methods tallies and family lines. Each was reproduced independently from the products (DuckDB) and matched.
- **Constants in the UI texts** (checked): "2003 to 2022", "20 years", "80%", "90%", "25th to 75th percentile" are the documented method constants (D-028); "0.5° grid" equals the metadata; "4 July 2002" is documented in `docs/DATA_SOURCES.md` section 9; the "265% ... about two and a half times" example in "How to read this" is the stored Indonesia 2015-09 value (264.86, shown as 265%) used as an illustration.
- **`0.5° grid` is a constant** in `content/ui.ts`, equal to the metadata today; if the grid changed it would not follow the metadata.
- **Coverage for countries and continents** is not shown until PR #94 (exact figure from the cell country); by design, not a defect.

## 4. Real-data rule (the Lead's rule on PR #75)

- `metadata.synthetic` is `false` (`/api/meta`); `validation_results.json` `synthetic` is `false`.
- No "SYNTHETIC" text on any page checked (the five cases, the methods page); the banner and the CSV file-name prefix appear only when a product says `synthetic: true`. The only "SYNTHETIC" strings in the production build `dist/` are that banner, the methods page's example-rows warning and the CSV prefix (found on 3 lines of 2 built chunks).
- No production file imports `__fixtures__` (`grep -rn "__fixtures__" app/src` outside `*.test.*` returns nothing).
- No hard-coded sample number in the new UI texts: every digit in `content/ui.ts`, `plainLanguage.ts`, `validationText.ts`, `evidenceText.ts`, `monthPicker.ts` and `sources.ts` is a documented method constant, a metadata-equal constant or the verified example above (see 3.2); the featured captions are generated from the products by `pipeline/featured_stories.py`.

## 5. Tests run

- App: `npm test` 666 passed (46 files); `npm run typecheck`, `npm run lint` (0 warnings) and `npm run build` clean.
- `pytest pipeline/tests/test_number_check.py`: 13 passed; `ruff check pipeline` and the two scripts of this PR: clean.

## 6. What a checker cannot reach (not verified)

- ECharts hover tooltips and the chart drawings (positions, colours): the tables of the same values were checked, not the pixels or every hover.
- The globe and satellite imagery pixels, the India outline drawing, the 375 px layout, keyboard paths and screen readers (the Lead's T-081 and T-074 cover these).
- Months and areas beyond the five cases and the app's own sampling: the function checker covers every `entity_month` row (see its report).
- Safari and Firefox; the offline copy.

## 7. Files

`docs/validation/T-078/expected.py` (expected values from the products), `docs/validation/T-078/compare.js` (the in-page comparison). To repeat: start the API on the products and the Vite dev server, run `expected.py`, open each case link and run `compare.js` (it reads `/_t078/expected.json` and `/_t078/compare.js` from the dev server's `public/` folder; copy both there for the run and delete them afterwards).
