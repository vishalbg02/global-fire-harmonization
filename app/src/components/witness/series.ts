import type { EntityMonth, ReasonCode, Witness } from '../../api/contract.ts'
import { WITNESSES, parseRawByWitness } from '../../api/contract.ts'

/** "2015-09" for a record. Used as the category axis label and as a stable key for months. */
export function monthLabel(record: Pick<EntityMonth, 'year' | 'month'>): string {
  return `${record.year}-${String(record.month).padStart(2, '0')}`
}

/** One label per record, in order. The chart's category axis. */
export function monthLabels(records: readonly EntityMonth[]): string[] {
  return records.map(monthLabel)
}

/** The values of one harmonized field, as stored. `null` is a gap, never a computed value. */
export function fieldSeries<K extends 'estimate' | 'ci90_low' | 'ci90_high' | 'baseline_median' | 'baseline_p25' | 'baseline_p75'>(
  records: readonly EntityMonth[],
  key: K,
): (number | null)[] {
  return records.map((r) => r[key])
}

/** `raw_combined_cell_days` as stored (never null in the contract). */
export function rawCombinedSeries(records: readonly EntityMonth[]): number[] {
  return records.map((r) => r.raw_combined_cell_days)
}

/**
 * The raw contribution of one witness for every month, decoded from each record's
 * `raw_by_witness` JSON string. `null` when the record has no map, or the witness is absent
 * from it that month (the witness did not contribute) — a gap, never zero.
 */
export function witnessSeries(records: readonly EntityMonth[], witness: Witness): (number | null)[] {
  return records.map((r) => {
    const decoded = parseRawByWitness(r.raw_by_witness, 'series record')
    return decoded?.[witness] ?? null
  })
}

/** The witnesses that contribute a raw value in at least one month of the series, in contract order. */
export function witnessesPresent(records: readonly EntityMonth[]): Witness[] {
  const present = new Set<Witness>()
  for (const record of records) {
    const decoded = parseRawByWitness(record.raw_by_witness, 'series record')
    if (decoded !== null) for (const w of Object.keys(decoded)) present.add(w as Witness)
  }
  return WITNESSES.filter((w) => present.has(w))
}

/** Month labels of records whose `reason_codes` includes `code`. */
export function monthsWithReason(records: readonly EntityMonth[], code: ReasonCode): string[] {
  return records.filter((r) => r.reason_codes.includes(code)).map(monthLabel)
}

/** Month labels of records marked provisional (`data_level` other than `SP`). */
export function provisionalMonths(records: readonly EntityMonth[]): string[] {
  return records.filter((r) => r.data_level !== 'SP').map(monthLabel)
}
