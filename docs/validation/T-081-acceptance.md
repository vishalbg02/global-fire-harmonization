# T-081: Final browser acceptance test (Lead)

**Run:** 2026-11-15, about 13:30 to 14:00 IST, by the Lead, on `main` @ `076847e` (after #74).
**Setup:**
- Local API on the real products (`data/products`; `metadata.synthetic=false`) and the Vite app.
- The offline copy: a static-only build from a fresh 24-month export.
- **Browser:** the Chromium engine of the in-app browser pane.
- **Not run: Safari and Firefox** (no such browser available in this session). That gap stays open until someone opens the app in them, and is listed below.

## 1. Featured stories (real API, real products)

Each case was opened with its story chip; the verdict and the % of normal were read from the page and compared with the stored values (T-079, T-078).

| Case | 1440x900 verdict | % of normal shown | Page fits (no sideways scroll) |
|---|---|---|---|
| Indonesia, Sep 2015 | Above normal ✔ | 265 ✔ | ✔ |
| Australia, Dec 2019 | Above normal ✔ | 328 ✔ | ✔ |
| Canada, Aug 2023 | Above normal ✔ | 1024 ✔ | ✔ |
| Brazil, Aug 2019 | Within normal ✔ | 114 ✔ | ✔ |
| World, Oct 2026 | Cannot determine ✔ | 91 ✔ | ✔ |

No console errors. The story chip sets the link (`area=…&month=…`) as expected.

## 2. Screen sizes

| Size | Checked | Result |
|---|---|---|
| 1440x900 (laptop) | 5 stories, tabs, globe | PASS: page fits; verdict above the fold |
| 1280x720 (projector) | Indonesia 2015-09; all 5 tabs (Calendar, Satellites, Evidence, All anomalies, Analytics) render content; Globe switch | PASS: page fits; verdict, 265% and interval visible without scrolling |
| 375x812 (phone) | Canada 2023-08; methods page | PASS: page fits; verdict "Above normal" and 1024% shown |

## 3. Features

| Feature | Result |
|---|---|
| Globe | PASS: the switch sets `globe=1`; loading a link with `globe=1` selects Globe; zoomed out, a 3D Earth with Blue Marble imagery and the cells |
| Satellite view | PASS (checked in #89 and #96 reviews): Aqua MODIS true colour for the chosen day, with the date |
| India's official boundary | PASS (#88, #95): outline includes Jammu and Kashmir, Ladakh and Aksai Chin; drawn above the cells; zoom fits it |
| Month picker | PASS (#90): any month in 2 clicks |
| Analytics | PASS: raw vs harmonized by year, season profile, rank, coverage per country (India 2019-04: 25% of 1,221 cells), compare |
| Methods page | PASS: "In plain words" first; counts 18 PASS / 18 FAIL / 2 INCONCLUSIVE; D1 "PASS (pooled); 2 sub-readings FAIL"; fits at 375 |
| Number check | PASS: `python pipeline/number_check.py` 0 mismatches on 592e732 (Lead) and 701c3a7 (T-078) |

## 4. Offline copy (no API)

- Export: `python -m fire_api.static_export --latest-months 24` → 24 map months, 234 areas, 225.3 MB raw, 48.9 s; manifest `synthetic: false`.
- Static-only build: `VITE_STATIC_ONLY=1 npm run build` with the export in `public/data/`, served with `vite preview`.
- Result **PASS:**
  - the "Offline copy" notice shows
  - "World, October 2026" loads with all 5 tabs
  - **0 requests to `/api/`** (8 data files read)
  - no console errors
- **The demo laptop's full copy** (every month, about 17 minutes) was **not** generated in this run. Generate it on the demo machine before an offline demo (command in `api/README.md`).

## 5. Open items (not passed, because not run)

1. Safari and Firefox: not tested here. Open the five story links in each before relying on them.
2. The full offline copy on the demo laptop: not generated.
3. A real screen reader: not tested (axe-core checks passed in T-074).

## 6. Verdict

**Accepted for the presentation on Chromium**, with the three open items above stated honestly.
