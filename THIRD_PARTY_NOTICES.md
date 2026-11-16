# Third-party data, imagery and fonts

The MIT License in [`LICENSE`](LICENSE) covers this project's own code and documentation. It does **not** relicense the third-party material below, which keeps its owners' terms. The derived data products in `data/products/` are computed from NASA FIRMS data; when you use them, acknowledge FIRMS as below.

| Material | Where in the repository | Terms |
|---|---|---|
| NASA FIRMS active-fire data: MODIS C6.1 (MYD14, MOD14), VIIRS 375 m (VNP14IMG, VJ114IMG) and near-real-time (MCD14DL, VNP14IMGT, VJ114IMGT); DOIs in [`README.md`](README.md) | Inputs to `pipeline/`; derived products in `data/products/` | NASA open data, provided "as is" with no restriction on reuse. NASA asks users to acknowledge FIRMS: *"We acknowledge the use of data and imagery from NASA's Fire Information for Resource Management System (FIRMS) (https://earthdata.nasa.gov/firms), part of NASA's Earth Science Data and Information System (ESDIS)."* |
| NASA GIBS imagery: Blue Marble shaded relief and bathymetry; MODIS Aqua Corrected Reflectance | Fetched by the browser at run time; nothing is stored in the repository | NASA open data; acknowledge NASA GIBS, part of NASA's ESDIS. |
| Natural Earth admin-0 boundaries, India point of view | `app/public/geo/` | Public domain (naturalearthdata.com). |
| GFED4s basis regions | Used by `pipeline/` to define the pooling regions | Cite van der Werf, G. R. et al. (2017), *Global fire emissions estimates during 1997–2016*, Earth System Science Data 9, 697–720. |
| IBM Plex Sans and IBM Plex Mono | `app/public/fonts/` | SIL Open Font License 1.1; the full text is in [`app/public/fonts/OFL.txt`](app/public/fonts/OFL.txt). |
| npm and Python packages (React, Vite, MapLibre GL, deck.gl, ECharts, terra-draw, FastAPI, DuckDB, pandas and others) | Installed from `app/package-lock.json` and `api/requirements.txt`; not committed | Each package's own license, as published with the package. |
