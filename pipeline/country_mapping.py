"""FIRMS country name -> ISO3 / continent mapping (T-009).

FIRMS archive rows carry only a country name taken from the file name (underscores
replaced by spaces by T-003). This module builds and checks pipeline/country_map.csv.

    # build the table (needs the Natural Earth zip and the normalized detections, both local)
    python pipeline/country_mapping.py build --ne path/to/ne_50m_admin_0_countries.zip
    # check that every name in the detections is mapped (and nothing else is)
    python pipeline/country_mapping.py check

Natural Earth (public domain) is used only as a reference list. Names it cannot resolve
are listed in MANUAL below, each with a note. Nothing is guessed silently: the builder
stops and lists every unresolved name.
"""
from __future__ import annotations

import argparse
import csv
import re
import struct
import sys
import unicodedata
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MAP_CSV = ROOT / "pipeline" / "country_map.csv"
DETECTIONS = ROOT / "data" / "interim" / "detections"
COLUMNS = ["firms_name", "iso3", "continent", "method", "note"]
CONTINENTS = {"AF", "AN", "AS", "EU", "NA", "OC", "SA"}
CONTINENT_CODE = {"Africa": "AF", "Antarctica": "AN", "Asia": "AS", "Europe": "EU", "North America": "NA",
                  "Oceania": "OC", "South America": "SA"}
# Natural Earth fields compared with the FIRMS name, in priority order. SOVEREIGNT is deliberately not
# used: it would map every territory to its sovereign state.
MATCH_FIELDS = ["NAME", "NAME_LONG", "NAME_EN", "BRK_NAME", "ADMIN", "FORMAL_EN"]

# Names resolved by hand: (iso3, continent, note). Continents of ocean territories follow the UN M49 region.
MANUAL: dict[str, tuple[str, str, str]] = {
    "Cote d Ivoire": ("CIV", "AF", "File name drops the apostrophe of Cote d'Ivoire"),
    "French Guiana": ("GUF", "SA", "Overseas department of France; not a Natural Earth country"),
    "Guadeloupe": ("GLP", "NA", "Overseas department of France; not a Natural Earth country"),
    "Martinique": ("MTQ", "NA", "Overseas department of France; not a Natural Earth country"),
    "Mayotte": ("MYT", "AF", "Overseas department of France; not a Natural Earth country"),
    "Reunion": ("REU", "AF", "Overseas department of France; not a Natural Earth country"),
    "Macedonia Former Yugoslav Republic of": ("MKD", "EU", "Former name of North Macedonia"),
    "Republic of Congo": ("COG", "AF", "Congo-Brazzaville; not the Democratic Republic of the Congo (COD)"),
    "Swaziland": ("SWZ", "AF", "Former name of Eswatini"),
    "Svalbard and Jan Mayen": ("SJM", "EU", "Not a Natural Earth country"),
    "South Georgia and South Sandwich Islands": ("SGS", "SA", "Natural Earth name differs; UN M49 puts it in South America"),
    "United States Minor Outlying Islands": ("UMI", "OC", "Mostly Pacific islands; UN M49 region is Oceania [needs Lead approval]"),
    "Kosovo": ("XKX", "EU", "No ISO 3166-1 code; XKX is the user-assigned code in common use [needs Lead approval]"),
    "French Southern and Antarctic Lands": ("ATF", "AF", "Natural Earth continent is 'Seven seas'; UN M49 region is Africa"),
    "Heard I and McDonald Islands": ("HMD", "OC", "Natural Earth continent is 'Seven seas'; UN M49 region is Oceania"),
    "Maldives": ("MDV", "AS", "Natural Earth continent is 'Seven seas'; UN M49 region is Asia"),
    "Mauritius": ("MUS", "AF", "Natural Earth continent is 'Seven seas'; UN M49 region is Africa"),
    "Saint Helena": ("SHN", "AF", "Natural Earth continent is 'Seven seas'; UN M49 region is Africa"),
    "Seychelles": ("SYC", "AF", "Natural Earth continent is 'Seven seas'; UN M49 region is Africa"),
}


def norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower()
    s = re.sub(r"[^a-z0-9 ]+", " ", s.replace("-", " ").replace("'", ""))
    return re.sub(r"\s+", " ", s).strip()


def read_dbf(data: bytes) -> list[dict[str, str]]:
    """Minimal dBase reader for the Natural Earth attribute table (UTF-8)."""
    n, header_len, rec_len = struct.unpack("<I", data[4:8])[0], struct.unpack("<H", data[8:10])[0], struct.unpack("<H", data[10:12])[0]
    fields, pos = [], 32
    while data[pos] != 0x0D:
        fields.append((data[pos:pos + 11].split(b"\0")[0].decode(), data[pos + 16]))
        pos += 32
    rows = []
    for i in range(n):
        rec = data[header_len + i * rec_len: header_len + (i + 1) * rec_len]
        if rec[:1] == b"*":
            continue
        p, row = 1, {}
        for name, ln in fields:
            row[name] = rec[p:p + ln].decode("utf-8", "replace").replace("\x00", "").strip()
            p += ln
        rows.append(row)
    return rows


def read_natural_earth(zip_path: Path) -> list[dict[str, str]]:
    with zipfile.ZipFile(zip_path) as z:
        dbf = next(n for n in z.namelist() if n.endswith(".dbf") and "/" not in n and ".." not in n)
        return read_dbf(z.read(dbf))


def valid_iso3(code: str) -> bool:
    return bool(re.fullmatch(r"[A-Z]{3}", code or ""))


def match_natural_earth(name: str, ne: list[dict[str, str]]) -> tuple[list[dict[str, str]], str]:
    """Return (distinct matching countries, field used). Field tiers are tried in priority order."""
    key = norm(name)
    for field in MATCH_FIELDS:
        hits = {r["ADM0_A3"]: r for r in ne if r.get(field) and norm(r[field]) == key}
        if hits:
            return list(hits.values()), field
    return [], ""


def build_rows(names: list[str], ne: list[dict[str, str]]) -> tuple[list[dict[str, str]], list[str]]:
    """Map every name. Returns (rows, problems); a non-empty problems list means the table is not complete."""
    rows, problems = [], []
    for name in sorted(names):
        if name in MANUAL:
            iso, cont, note = MANUAL[name]
            rows.append({"firms_name": name, "iso3": iso, "continent": cont, "method": "MANUAL", "note": note})
            continue
        hits, field = match_natural_earth(name, ne)
        if len(hits) != 1:
            problems.append(f"{name}: {'conflict between ' + ', '.join(sorted(h['ADM0_A3'] for h in hits)) if hits else 'no match'}"
                            " (add it to MANUAL)")
            continue
        r = hits[0]
        iso = next((c for c in (r.get("ISO_A3", ""), r.get("ISO_A3_EH", "")) if valid_iso3(c)), "")
        cont = CONTINENT_CODE.get(r.get("CONTINENT", ""), "")
        if not iso or not cont:
            problems.append(f"{name}: Natural Earth has no usable code or continent (ISO_A3={r.get('ISO_A3')}, "
                            f"CONTINENT={r.get('CONTINENT')}); add it to MANUAL")
            continue
        rows.append({"firms_name": name, "iso3": iso, "continent": cont, "method": "NATURAL_EARTH",
                     "note": f"matched Natural Earth {field} '{r[field]}' ({r['ADM0_A3']})"})
    return rows, problems


def validate_rows(rows: list[dict[str, str]]) -> list[str]:
    problems = []
    names = [r["firms_name"] for r in rows]
    if len(names) != len(set(names)):
        problems.append("duplicate firms_name")
    for r in rows:
        if not valid_iso3(r["iso3"]):
            problems.append(f"{r['firms_name']}: bad iso3 {r['iso3']!r}")
        if r["continent"] not in CONTINENTS:
            problems.append(f"{r['firms_name']}: bad continent {r['continent']!r}")
        if r["method"] not in ("NATURAL_EARTH", "MANUAL"):
            problems.append(f"{r['firms_name']}: bad method {r['method']!r}")
        if r["method"] == "MANUAL" and not r["note"]:
            problems.append(f"{r['firms_name']}: manual row without a note")
    seen: dict[str, str] = {}
    for r in rows:  # two FIRMS names must not claim the same ISO3
        if r["iso3"] in seen:
            problems.append(f"{r['iso3']} used by both {seen[r['iso3']]!r} and {r['firms_name']!r}")
        seen[r["iso3"]] = r["firms_name"]
    return problems


def write_map(rows: list[dict[str, str]], path: Path = MAP_CSV) -> None:
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLUMNS, lineterminator="\n")
        w.writeheader()
        w.writerows(sorted(rows, key=lambda r: r["firms_name"]))


def read_map(path: Path = MAP_CSV) -> list[dict[str, str]]:
    with open(path, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def names_in_detections(folder: Path = DETECTIONS) -> list[str]:
    import duckdb
    pattern = (folder / "sensor=*" / "year=*" / "detections.parquet").as_posix()
    rows = duckdb.sql(f"SELECT DISTINCT country_name FROM read_parquet('{pattern}') WHERE country_name IS NOT NULL").fetchall()
    return sorted(r[0] for r in rows)


def check(names: list[str], rows: list[dict[str, str]]) -> list[str]:
    """Every name in the data is mapped (100%), and the table has no names the data lacks."""
    problems = validate_rows(rows)
    mapped = {r["firms_name"] for r in rows}
    problems += [f"unmapped name in the data: {n}" for n in sorted(set(names) - mapped)]
    problems += [f"table name not in the data: {n}" for n in sorted(mapped - set(names))]
    return problems


def main() -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("build")
    b.add_argument("--ne", type=Path, required=True, help="ne_50m_admin_0_countries.zip")
    sub.add_parser("check")
    args = ap.parse_args()
    names = names_in_detections()
    if args.cmd == "build":
        rows, problems = build_rows(names, read_natural_earth(args.ne))
        problems += validate_rows(rows) if not problems else []
        if problems:
            print("\n".join(problems))
            return 1
        write_map(rows)
        manual = sum(r["method"] == "MANUAL" for r in rows)
        print(f"wrote {MAP_CSV.name}: {len(rows)} names ({len(rows) - manual} Natural Earth, {manual} manual)")
        return 0
    problems = check(names, read_map())
    print("\n".join(problems) if problems else f"all {len(names)} names in the detections are mapped")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
