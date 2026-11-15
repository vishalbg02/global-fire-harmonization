/**
 * The computations of the analytics panel (T-083). Pure functions over stored values: sums, ranks, shares and the percentiles that
 * the products already hold. No trend, regression or forecast. Imports are types only, so Node can run this file directly
 * (pipeline/tests/test_analytics_check.py compares it with an independent recomputation from the products).
 */
import type { EntityMonth, MapCell } from '../../api/contract.ts'
import type { CellAreas } from '../../api/mapColumns.ts'

export const MONTH_NAMES = [
  'January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December',
] as const

/** The months in which a satellite joins the record (docs/DATA_SOURCES.md section 4, FIRMS FAQ). */
export const SATELLITE_JOINS: readonly { year: number; month: number; label: string }[] = [
  { year: 2012, month: 1, label: 'S-NPP VIIRS joins (2012-01)' },
  { year: 2018, month: 4, label: 'NOAA-20 VIIRS joins (2018-04)' },
]

type MonthRecord = Pick<EntityMonth, 'year' | 'month' | 'estimate' | 'raw_combined_cell_days' | 'data_level'>

// ---------------------------------------------------------------------------------------------------- 1. raw against harmonized by year
export interface AnnualPoint {
  year: number
  /** Months of this year that have an estimate: both sums cover exactly these months. */
  monthsUsed: number
  /** Sum of the monthly harmonized estimates (intervals are not combined). */
  harmonizedSum: number
  /** Sum of the raw combined cell-days of the same months (the unconverted merge of all satellites). */
  rawSum: number
  /** Fewer than 12 months used: the year is partial (the record starts in 2002-07; recent months may be missing). */
  partial: boolean
  provisional: boolean
}

export function annualSeries(records: readonly MonthRecord[]): AnnualPoint[] {
  const byYear = new Map<number, AnnualPoint>()
  for (const r of records) {
    if (r.estimate === null) continue
    const p = byYear.get(r.year) ?? { year: r.year, monthsUsed: 0, harmonizedSum: 0, rawSum: 0, partial: true, provisional: false }
    p.monthsUsed += 1
    p.harmonizedSum += r.estimate
    p.rawSum += r.raw_combined_cell_days
    p.provisional = p.provisional || r.data_level !== 'SP'
    byYear.set(r.year, p)
  }
  return [...byYear.values()]
    .map((p) => ({ ...p, partial: p.monthsUsed < 12 }))
    .sort((a, b) => a.year - b.year)
}

// ---------------------------------------------------------------------------------------------------------------- 2. season profile
export interface SeasonPoint {
  month: number
  p25: number | null
  median: number | null
  p75: number | null
  /** The selected year's harmonized estimate for this calendar month, null if none. */
  selected: number | null
}

type SeasonRecord = MonthRecord & Pick<EntityMonth, 'baseline_p25' | 'baseline_median' | 'baseline_p75'>

/** The baseline of a calendar month is the same in every year (2003 to 2022), so any record of the month supplies it; the selected year first. */
export function seasonProfile(records: readonly SeasonRecord[], year: number): SeasonPoint[] {
  return MONTH_NAMES.map((_, i) => {
    const month = i + 1
    const ofMonth = records.filter((r) => r.month === month)
    const sel = ofMonth.find((r) => r.year === year)
    const base = (sel !== undefined && sel.baseline_median !== null ? sel : ofMonth.find((r) => r.baseline_median !== null)) ?? null
    return {
      month,
      p25: base?.baseline_p25 ?? null,
      median: base?.baseline_median ?? null,
      p75: base?.baseline_p75 ?? null,
      selected: sel?.estimate ?? null,
    }
  })
}

// ----------------------------------------------------------------------------------------------------------------------------- 3. rank
export interface RankResult {
  month: number
  year: number
  value: number
  /** Competition rank: 1 plus the number of years with a strictly larger estimate. */
  rank: number
  /** Years with an estimate for this calendar month. */
  of: number
  /** Other years with exactly the same estimate (they share the rank). */
  tiedWith: number[]
  /** Years inside the record's range with no estimate for this calendar month. */
  missingYears: number[]
  provisional: boolean
}

export function rankInMonth(records: readonly MonthRecord[], year: number, month: number): RankResult | null {
  const ofMonth = records.filter((r) => r.month === month)
  const withEstimate = ofMonth.filter((r) => r.estimate !== null) as (MonthRecord & { estimate: number })[]
  const sel = withEstimate.find((r) => r.year === year)
  if (sel === undefined) return null
  const years = records.map((r) => r.year)
  const first = Math.min(...years)
  const last = Math.max(...years)
  const have = new Set(withEstimate.map((r) => r.year))
  const missingYears: number[] = []
  for (let y = first; y <= last; y++) if (!have.has(y)) missingYears.push(y)
  return {
    month,
    year,
    value: sel.estimate,
    rank: 1 + withEstimate.filter((r) => r.estimate > sel.estimate).length,
    of: withEstimate.length,
    tiedWith: withEstimate.filter((r) => r.year !== year && r.estimate === sel.estimate).map((r) => r.year).sort((a, b) => a - b),
    missingYears,
    provisional: sel.data_level !== 'SP',
  }
}

export function ordinal(n: number): string {
  const tens = n % 100
  if (tens >= 11 && tens <= 13) return `${n}th`
  return `${n}${({ 1: 'st', 2: 'nd', 3: 'rd' } as Record<number, string>)[n % 10] ?? 'th'}`
}

/** "September 2015 is the 1st highest September of the record (24 years with an estimate)." plus the stated ties and gaps. */
export function rankText(r: RankResult): string[] {
  const name = MONTH_NAMES[r.month - 1]
  const lines = [`${name} ${r.year} is the ${ordinal(r.rank)} highest ${name} of the record (${r.of} years with an estimate).`]
  if (r.tiedWith.length > 0) lines.push(`Tied with ${r.tiedWith.join(', ')}: the same estimate.`)
  if (r.missingYears.length > 0) lines.push(`No estimate for ${name} in ${r.missingYears.join(', ')}.`)
  if (r.provisional) lines.push('This month is provisional (near-real-time data) and may change.')
  return lines
}

// ------------------------------------------------------------------------------------------------------------------------ 4. coverage
export type Box = readonly [number, number, number, number]

export interface Coverage {
  cells: number
  determinable: number
  /** determinable / cells, in 0..1. */
  share: number
  byVerdict: Record<string, number>
}

/** Cells whose centre lies inside the box (edges inclusive: the API's rule for custom areas), counted by verdict. */
export function coverage(
  cells: readonly Pick<MapCell, 'lat_min' | 'lat_max' | 'lon_min' | 'lon_max' | 'verdict'>[],
  box: Box | null,
): Coverage | null {
  const [w, s, e, n] = box ?? [-180, -90, 180, 90]
  const byVerdict: Record<string, number> = {}
  let total = 0
  for (const c of cells) {
    const lat = (c.lat_min + c.lat_max) / 2
    const lon = (c.lon_min + c.lon_max) / 2
    if (lon < w || lon > e || lat < s || lat > n) continue
    total += 1
    byVerdict[c.verdict] = (byVerdict[c.verdict] ?? 0) + 1
  }
  if (total === 0) return null
  const determinable = total - (byVerdict.CANNOT_DETERMINE ?? 0)
  return { cells: total, determinable, share: determinable / total, byVerdict }
}

// ------------------------------------------------------------------------------------------------------------------------ 5. compare
export interface ComparePoint {
  label: string
  a: number | null
  b: number | null
}

const label = (r: Pick<EntityMonth, 'year' | 'month'>) => `${r.year}-${String(r.month).padStart(2, '0')}`

/** Monthly % of normal of two areas on the months of area A's record (a missing value stays null, never 0). */
export function compareSeries(a: readonly EntityMonth[], b: readonly EntityMonth[]): ComparePoint[] {
  const bByLabel = new Map(b.map((r) => [label(r), r.pct_of_normal]))
  return a.map((r) => ({ label: label(r), a: r.pct_of_normal, b: bByLabel.get(label(r)) ?? null }))
}

// ------------------------------------------------------------------------------------------ 4b. exact coverage of a country or a continent
/**
 * The coverage of a country or a continent: the cells whose stored country (or continent) is the area, counted by verdict. The areas come
 * from the cell list (cells.parquet), so a neighbour's cells are never counted. Null when the area has no cell in the month.
 */
export function coverageInArea(
  cells: readonly Pick<MapCell, 'cell_id' | 'verdict'>[],
  areas: CellAreas,
  entityType: 'COUNTRY' | 'CONTINENT',
  entityId: string,
): Coverage | null {
  const column = entityType === 'COUNTRY' ? areas.country_iso3 : areas.continent
  const inArea = new Set<string>()
  for (let i = 0; i < areas.cell_id.length; i++) if (column[i] === entityId) inArea.add(areas.cell_id[i] as string)
  const byVerdict: Record<string, number> = {}
  let total = 0
  for (const c of cells) {
    if (!inArea.has(c.cell_id)) continue
    total += 1
    byVerdict[c.verdict] = (byVerdict[c.verdict] ?? 0) + 1
  }
  if (total === 0) return null
  const determinable = total - (byVerdict.CANNOT_DETERMINE ?? 0)
  return { cells: total, determinable, share: determinable / total, byVerdict }
}
