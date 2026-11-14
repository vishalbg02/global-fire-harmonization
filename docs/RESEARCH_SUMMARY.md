# Research Summary (discovery phase, 2026-11-14)

This preserves the discovery research so it does not depend on chat history.

## 1. Challenge interpretation

- **Literal ask:** a web app with a harmonized MODIS + VIIRS burning-activity calendar (early 2000s → present). It should support area selection, current activity vs the historical median, accessible colour ramps and CSV download. Target users are emergency responders, scientists, land managers and firefighters.
- **Underlying problem:** hotspot counts measure what satellites could see, not how much burned. Several things changed over 25 years for reasons unrelated to fire:
  - VIIRS arrived in 2012.
  - Satellites were added in 2018 and 2024.
  - S-NPP ended on 2 Nov 2026.
  - Terra and Aqua are drifting.
  - People changed when they burn (Punjab).
- **What users need underneath:** to know whether a change is real.
- **Why now:** S-NPP ended in November 2026, and MODIS ends in 2026–27. The record is breaking twice.

## 2. Competitor landscape

| Solution | Strength | Gap |
|---|---|---|
| NASA FIRMS | Authoritative NRT and archive data | No harmonization or climatology |
| NASA Worldview | Imagery context | No statistics |
| Global Forest Watch | VIIRS alerts vs historical average | VIIRS-only baseline (2012+); no uncertainty |
| GWIS (JRC) | Country profiles; MODIS and VIIRS counts vs a 10-year average | Sensors kept separate; country-level |
| CAMS GFAS / GFED / FireCCI | Rigorous gridded science | Not built for responders |
| Other 2026 teams (e.g. firelens, flare-chronos, Chronofire, pyfire-watch, squadron-zero, ignis) | Calibrated calendars, H3 grids, quantile mapping, AI agents | Mostly in-sample validation; claims judges cannot verify |

**Our differentiation:**
- Validation you can see (pre-registered, failures published).
- Probability-based verdicts with "cannot determine".
- Honesty about observation timing.
- Explicit treatment of witness changes.

## 3. Key scientific findings

- VIIRS 375 m detects many more small fires than MODIS (Schroeder et al. 2014). The VIIRS:MODIS ratio depends on fire size and regime.
- Aqua MODIS and S-NPP VIIRS share a ~13:30 overpass, ideal for the 2012–~2021 overlap. NOAA-20 is ~50 min earlier.
- NASA built a MODIS-heritage 750 m VIIRS product for continuity (not in FIRMS). FIRMS itself distributes the 375 m product.
- Mature methods from neighbouring fields apply:
  - climate-record homogenization benchmarking with synthetic breaks (Venema et al. 2012)
  - ESA CCI satellite merging (CDF matching, inverse-uncertainty weighting, triple collocation)
- In Punjab, burning moved later in the day (ISRO/SAC; iFOREST), so polar-orbiter counts can fall without burning falling.

## 4. Concepts evaluated

There were 19 concepts, scored on the Lead's weighted criteria. Constant Witness scored highest at first (8.32). After the critical review it was rescored to 6.95, and Many Witnesses + Witness Stand scored 8.06. "D-lite", the hackathon-scope version, scored 8.00. Rejected or deferred concepts include:
- historical analogues
- regime atlas
- silence map
- fire sonification
- AI chatbot (lowest score: low originality, risk of hallucinations)

## 5. Sources

- Challenge: https://www.spaceappschallenge.org/2026/challenges/modis-and-viirs-hot-spots/
- Submission guide: https://www.spaceappschallenge.org/resources/project-submission-guide/
- FIRMS: https://www.earthdata.nasa.gov/data/tools/firms · FAQ: https://www.earthdata.nasa.gov/data/tools/firms/faq · API: https://firms.modaps.eosdis.nasa.gov/api/area/
- LAADS MODIS→VIIRS transition: https://ladsweb.modaps.eosdis.nasa.gov/learn/modis-to-viirs-transition
- CAMS on MODIS drift: https://atmosphere.copernicus.eu/drifting-away-modis-cams-global-fire-assimilation-system
- GFW fire trends: https://www.globalforestwatch.org/blog/data-and-tools/wildfire-trends-gfw-fire-data/
- GWIS: https://gwis.jrc.ec.europa.eu/applications
- VNP64A1 in FIRMS: https://www.earthdata.nasa.gov/news/blog/viirs-global-burned-area-product-added-firms
- VIIRS active fire products: https://viirsland.gsfc.nasa.gov/Products/NASA/FireESDR.html
- Competitor repos: https://github.com/shahmirkhan106/firelens · https://github.com/the-aris-club/flare-chronos · https://github.com/shahedrayhan23/Chronofire · https://github.com/Thay32-Heng/pyfire-watch
- Further science references are listed in `SCIENTIFIC_METHODOLOGY.md` §9.
