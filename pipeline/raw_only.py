"""Raw-only `cell_month_harmonized` and `entity_month` in the contract shape (T-014a).

Until T-013 and T-014 deliver the harmonized products, the app gets the real raw observations in the exact shape of
docs/DATA_CONTRACT.md 0.1.1 (D-026) section 3 and 4. Only the raw fields are filled. Every harmonized field is null,
`witnesses_used` is empty, the verdict is CANNOT_DETERMINE and `reason_codes` is [NOT_HARMONIZED]. The rows are recognised by a `method_version`
that ends in `-raw-only`. T-014 replaces these files.

    python pipeline/raw_only.py            # reads and writes data/products/, then validates with contract_check --real
"""
from __future__ import annotations

import datetime as dt
import json
import sys
from dataclasses import dataclass
from pathlib import Path

import duckdb
import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))

METHOD_VERSION = "0.1.0-raw-only"
CONTRACT_VERSION = "0.1.1"
CONTINENT_NAMES = {"AF": "Africa", "AN": "Antarctica", "AS": "Asia", "EU": "Europe", "NA": "North America",
                   "OC": "Oceania", "SA": "South America"}
CITATION = ("We acknowledge the use of data and imagery from NASA's Fire Information for Resource Management System (FIRMS) "
            "(https://earthdata.nasa.gov/firms), part of NASA's Earth Science Data and Information System (ESDIS), and from LANCE. "
            "FIRMS data are provided \"as is\". These files hold raw observations only: no harmonized estimate, baseline or verdict.")
# Every harmonized field of section 3, null in the raw-only files.
NULL_FLOATS = ["estimate", "ci90_low", "ci90_high", "sd", "disagreement_scale", "baseline_median", "baseline_p25",
               "baseline_p75", "pct_of_normal", "p_above", "p_below", "p_within"]


@dataclass
class Paths:
    products: Path = ROOT / "data" / "products"
    country_map: Path = ROOT / "pipeline" / "country_map.csv"
    raw: Path = ROOT / "data" / "raw"
    tmp: Path = ROOT / "data" / "interim" / "_duckdb_tmp"


def _nulls(names: list[str]) -> str:
    return ", ".join(f"CAST(NULL AS DOUBLE) AS {c}" for c in names)


def build(paths: Paths | None = None) -> dict:
    """Write cell_month_harmonized.parquet and entity_month.parquet next to the inputs; return a report."""
    paths = paths or Paths()
    paths.tmp.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect()
    con.execute(f"SET temp_directory='{paths.tmp.as_posix()}'")
    con.execute("SET memory_limit='4GB'")
    cmw = f"read_parquet('{(paths.products / 'cell_month_witness.parquet').as_posix()}')"
    cells = f"read_parquet('{(paths.products / 'cells.parquet').as_posix()}')"
    names = f"read_csv('{paths.country_map.as_posix()}', header=true)"
    con.execute(f"""CREATE TEMP TABLE w AS SELECT cell_id, year, month, witness, sum(cell_days) AS s, min(data_level) AS lo, max(data_level) AS hi
                    FROM {cmw} WHERE daynight = 'ALL' GROUP BY ALL""")
    nulls_a, nulls_b = _nulls(NULL_FLOATS[:4]), _nulls(NULL_FLOATS[4:])
    cont = ", ".join(f"('{k}', '{v}')" for k, v in CONTINENT_NAMES.items())
    con.execute(f"CREATE TEMP TABLE continents AS SELECT * FROM (VALUES {cont}) t(code, name)")
    con.execute(f"""CREATE TEMP TABLE members AS
        SELECT 'COUNTRY' AS entity_type, c.country_iso3 AS entity_id, any_value(n.firms_name) AS entity_name, c.cell_id
          FROM {cells} c JOIN {names} n ON n.iso3 = c.country_iso3 WHERE c.country_iso3 IS NOT NULL GROUP BY c.country_iso3, c.cell_id
        UNION ALL
        SELECT 'CONTINENT', c.continent, k.name, c.cell_id FROM {cells} c JOIN continents k ON k.code = c.continent
        UNION ALL
        SELECT 'GLOBAL', 'GLOBAL', 'World', c.cell_id FROM {cells} c""")
    # the harmonized columns shared by both tables, in contract order (estimate .. method_version)
    harm = f"""{nulls_a}, {{raw}} AS raw_combined_cell_days, CAST([] AS VARCHAR[]) AS witnesses_used, CAST(0 AS BIGINT) AS n_witnesses,
               {nulls_b}, 'CANNOT_DETERMINE' AS verdict, CAST(['NOT_HARMONIZED'] AS VARCHAR[]) AS reason_codes, {{dl}} AS data_level,
               '{METHOD_VERSION}' AS method_version"""
    cell_sql = f"""SELECT cell_id, year, month, {harm.format(raw='CAST(sum(s) AS BIGINT)', dl="CASE WHEN min(lo) = max(hi) THEN min(lo) ELSE 'MIXED' END")}
                   FROM w GROUP BY cell_id, year, month ORDER BY cell_id, year, month"""
    cell_path = paths.products / "cell_month_harmonized.parquet"
    con.execute(f"COPY ({cell_sql}) TO '{cell_path.as_posix()}' (FORMAT parquet, COMPRESSION zstd)")
    con.execute("""CREATE TEMP TABLE ncells AS SELECT entity_type, entity_id, count(*) AS n FROM members GROUP BY ALL""")
    con.execute("""CREATE TEMP TABLE ew AS
        SELECT m.entity_type, m.entity_id, any_value(m.entity_name) AS entity_name, w.year, w.month, w.witness,
               sum(w.s) AS s, min(w.lo) AS lo, max(w.hi) AS hi
        FROM w JOIN members m USING (cell_id) GROUP BY m.entity_type, m.entity_id, w.year, w.month, w.witness""")
    ent_sql = f"""SELECT ew.entity_type, ew.entity_id, any_value(ew.entity_name) AS entity_name, ew.year, ew.month,
                  {harm.format(raw='CAST(sum(ew.s) AS BIGINT)', dl="CASE WHEN min(ew.lo) = max(ew.hi) THEN min(ew.lo) ELSE 'MIXED' END")},
                  CAST(any_value(n.n) AS BIGINT) AS n_cells,
                  '{{' || string_agg('"' || ew.witness || '": ' || CAST(ew.s AS VARCHAR), ', ' ORDER BY ew.witness) || '}}' AS raw_by_witness
                  FROM ew JOIN ncells n USING (entity_type, entity_id)
                  GROUP BY ew.entity_type, ew.entity_id, ew.year, ew.month ORDER BY 1, 2, 4, 5"""
    ent_path = paths.products / "entity_month.parquet"
    con.execute(f"COPY ({ent_sql}) TO '{ent_path.as_posix()}' (FORMAT parquet, COMPRESSION zstd)")
    report = {
        "cell_rows": pq.ParquetFile(cell_path).metadata.num_rows,
        "entity_rows": pq.ParquetFile(ent_path).metadata.num_rows,
        "entities": dict(con.execute("SELECT entity_type, count(*) FROM ncells GROUP BY 1 ORDER BY 1").fetchall()),
    }
    meta = write_metadata(con, paths, w_table="w", cells=cells)
    report["metadata"] = meta
    return report


def _ym(v: int) -> str:
    return f"{v // 100}-{v % 100:02d}"


def snapshot_dates(raw: Path) -> dict:
    """Dates of the downloaded zips and of the 2026 API pull, from the modification times of the saved files."""
    def newest(folder: Path, pattern: str) -> str | None:
        files = list(folder.glob(pattern))
        return dt.date.fromtimestamp(max(f.stat().st_mtime for f in files)).isoformat() if files else None
    return {"zips_downloaded": newest(raw / "zips", "*.zip"), "api_pulled": newest(raw / "api_2026", "*")}


def write_metadata(con, paths: Paths, w_table: str, cells: str, generated_at: str | None = None) -> dict:
    first, last = con.execute(f"SELECT min(year * 100 + month), max(year * 100 + month) FROM {w_table}").fetchone()
    prov = [_ym(v) for (v,) in con.execute(
        f"SELECT DISTINCT year * 100 + month FROM {w_table} WHERE hi IN ('NRT', 'MIXED') ORDER BY 1").fetchall()]
    witnesses = [x for (x,) in con.execute(f"SELECT DISTINCT witness FROM {w_table} ORDER BY 1").fetchall() if x != "TERRA_MODIS"]
    lat0, lat1 = con.execute(f"SELECT lat_min, lat_max FROM {cells} LIMIT 1").fetchone()
    meta = {
        "contract_version": CONTRACT_VERSION, "method_version": METHOD_VERSION, "synthetic": False,
        "generated_at": generated_at or dt.datetime.now(dt.UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "grid": {"analysis_deg": round(lat1 - lat0, 6), "fine_deg": 0.05},
        "baseline_years": [], "first_month": _ym(first), "latest_month": _ym(last), "provisional_months": prov,
        "witnesses": witnesses, "data_snapshot": snapshot_dates(paths.raw), "citation": CITATION,
    }
    (paths.products / "metadata.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    (paths.products / "validation_results.json").write_text(json.dumps(
        {"contract_version": CONTRACT_VERSION, "method_version": METHOD_VERSION, "generated_at": meta["generated_at"],
         "synthetic": False, "tests": []}, indent=2), encoding="utf-8")
    return meta


def main() -> int:
    import contract_check as cc
    paths = Paths()
    report = build(paths)
    print(json.dumps({k: v for k, v in report.items() if k != "metadata"}, indent=1))
    errors = cc.check_dir(paths.products, real=True, only=("cells", "cell_month_harmonized", "entity_month"))
    print("\n".join(errors) if errors else "raw-only products validate against the contract (real-data mode)")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
