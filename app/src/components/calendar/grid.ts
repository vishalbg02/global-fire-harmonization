import { ContractError } from '../../api/contract.ts'
import type { EntityMonth } from '../../api/contract.ts'
import { monthKey } from '../../state/months.ts'

/**
 * outside:   before the first month of the record or after the latest month (never zero).
 * no-record: inside the record, but the series has no record for that month ("no data").
 * record:    a stored entity_month record.
 */
export type CellKind = 'outside' | 'no-record' | 'record'

export interface CalendarCell {
  year: number
  month: number
  kind: CellKind
  record: EntityMonth | null
  /** In metadata.provisional_months, or the record's data_level is not SP. */
  provisional: boolean
}

export interface CalendarRow {
  year: number
  cells: CalendarCell[]
}

function parts(ym: string): { year: number; month: number } {
  const [y, m] = ym.split('-')
  return { year: Number(y), month: Number(m) }
}

/** Years from the first month's year to the latest month's year, 12 months each. */
export function buildCalendarGrid(
  records: readonly EntityMonth[],
  firstMonth: string,
  latestMonth: string,
  provisionalMonths: readonly string[],
): CalendarRow[] {
  const byMonth = new Map<string, EntityMonth>()
  for (const r of records) {
    const key = monthKey(r.year, r.month)
    if (byMonth.has(key)) throw new ContractError(`series: more than one record for ${key}`)
    byMonth.set(key, r)
  }
  const first = parts(firstMonth)
  const latest = parts(latestMonth)
  const firstKey = monthKey(first.year, first.month)
  const latestKey = monthKey(latest.year, latest.month)
  const provisional = new Set(provisionalMonths)

  const rows: CalendarRow[] = []
  for (let year = first.year; year <= latest.year; year += 1) {
    const cells: CalendarCell[] = []
    for (let month = 1; month <= 12; month += 1) {
      const key = monthKey(year, month)
      const record = byMonth.get(key) ?? null
      // ISO year-month strings sort correctly as text.
      const inside = key >= firstKey && key <= latestKey
      cells.push({
        year,
        month,
        kind: !inside ? 'outside' : record === null ? 'no-record' : 'record',
        record,
        provisional: inside && (provisional.has(key) || (record !== null && record.data_level !== 'SP')),
      })
    }
    rows.push({ year, cells })
  }
  return rows
}

/**
 * The one maximum of the colour scale: the largest value among the raw combined counts and the
 * non-null harmonized estimates of the series (0 if there is none). Both sources share it, so
 * switching between them never rescales the colours. Nothing is converted.
 */
export function maxActivity(records: readonly EntityMonth[]): number {
  let max = 0
  for (const r of records) {
    max = Math.max(max, r.raw_combined_cell_days, r.estimate ?? 0)
  }
  return max
}
