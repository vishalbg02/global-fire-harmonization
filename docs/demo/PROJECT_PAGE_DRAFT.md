# Space Apps project page: draft text (T-062)

Ready to paste into the Space Apps project page. Posting it on the site is the Lead's step (outside the repository). Every number is a stored value or a measured result, with its source in the repository.

---

## Project name
Global Fire Harmonization (Many Witnesses)

## Challenge
Harmonization of MODIS and VIIRS Hot Spots (NASA Space Apps Challenge 2026)

## High-level summary (about 150 words)
NASA's FIRMS fire record comes from several satellites whose sensitivity differs: VIIRS (375 m) detects far more small fires than MODIS (1 km), and satellites join, drift and end. Adding the raw counts makes fire activity seem to jump whenever a satellite changes. We treat each satellite as a witness: we convert Aqua MODIS, S-NPP VIIRS and NOAA-20 VIIRS to one scale using the years they overlapped, combine them with honest uncertainty, and compare every area and month with the same month in 2003–2022.

The web app gives a verdict for any country, continent, the world or a custom area, July 2002 to November 2026: above, within or below normal, "cannot determine" or "no detected activity", each with a probability, a 90% interval, the satellites used and the reasons. We published our pre-registered validation: 38 results, 18 pass, 18 fail, 2 inconclusive.

## What it does
- **Global map and globe** on NASA Blue Marble imagery, with a true-colour Aqua MODIS satellite view of any day.
- **Verdict and evidence:** % of normal, probability, interval, satellites used, reasons in plain words, source line.
- **Calendar** (years by months), **satellite comparison**, **anomaly ranking**, **Analytics** (raw vs harmonized by year, season profile, rank, coverage, compare), **CSV export**, **custom rectangle and polygon areas**.
- **Methods and validation page** with every result, failures included.
- Works offline from a static copy.

## How we built it
- **Data:** the complete NASA FIRMS archive (MODIS C6.1; VIIRS 375 m S-NPP and NOAA-20) plus the 2026 near-real-time API; about 582 million detections, gridded to 0.5° (56,238 active cells, 293 months).
- **Method:** satellite-to-Aqua conversion by region, season and day/night with partial pooling, fitted on overlap years. Gas flares and volcanoes are masked; outages come from FIRMS's own table. The witnesses are combined with a disagreement-aware uncertainty, and the baseline is 2003–2022.
- **Stack:** Python (DuckDB, pandas, NumPy), FastAPI, React + TypeScript, MapLibre and deck.gl, ECharts. About 1,500 automated tests, and a number check of 6.49 million displayed values with 0 mismatches.

## What we learned (honest results)
- **Satellite-change steps are removed:** within 10% in 14 of 14 regions at 2012 (B1 PASS); the satellites agree in 97.6% of region-months (C1 PASS).
- **Extreme months are under-converted:** converted S-NPP reads 20–40% low in very large fires (A1 FAIL). We diagnosed it, built a fix (v0.2), and our own pre-registered rule rejected it, so the limitation is stated in the app.

## Space agency data used
- NASA FIRMS (https://www.earthdata.nasa.gov/data/tools/firms), with these products:
  - MODIS Collection 6.1 active fire: Aqua MYD14 (doi:10.5067/MODIS/MYD14.061); Terra MOD14 (doi:10.5067/MODIS/MOD14.061), raw view only
  - VIIRS 375 m active fire: S-NPP VNP14IMG (doi:10.5067/VIIRS/VNP14IMG.002); NOAA-20 VJ114IMG (doi:10.5067/VIIRS/VJ114IMG.002)
  - Near-real-time: MCD14DL (doi:10.5067/FIRMS/MODIS/MCD14DL.NRT.0061); VNP14IMGT (doi:10.5067/FIRMS/VIIRS/VNP14IMGT_NRT.002); VJ114IMGT (doi:10.5067/FIRMS/VIIRS/VJ114IMGT_NRT.002)
- NASA GIBS imagery: Blue Marble shaded relief and bathymetry; MODIS Aqua Corrected Reflectance true colour.

## Other resources
- GFED4s basis regions (van der Werf et al., 2017, *Earth System Science Data* 9, 697–720), for pooling.
- Natural Earth admin-0 boundaries, India point of view (official boundary of India), public domain.
- Open-source software: DuckDB, FastAPI, React, MapLibre GL JS, deck.gl, Apache ECharts, IBM Plex fonts.

## Links
- Repository: https://github.com/vishalbg02/global-fire-harmonization (visibility: the Lead's decision, T-064)
- Demo video: to add (T-061)

## Use of AI
Follow the Space Apps rules for disclosing the use of AI tools, as the Lead decides. No AI-generated imagery is used; all imagery is NASA's.
