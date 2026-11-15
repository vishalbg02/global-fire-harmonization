import { describe, expect, it } from 'vitest'
import { latestDeterminableMonth } from './initialMonth.ts'
import type { DeterminableRecord } from './initialMonth.ts'

// SYNTHETIC test data. Not NASA observations.
const rec = (year: number, month: number, estimate: number | null, reason_codes: string[] = []): DeterminableRecord => ({
  year,
  month,
  estimate,
  reason_codes,
})

describe('latestDeterminableMonth', () => {
  it('skips the newest month when it has no estimate and an outage (the all-grey month)', () => {
    const series = [
      rec(2026, 8, 220, ['PROVISIONAL_NRT', 'WIDE_INTERVAL']),
      rec(2026, 9, 150, ['PROVISIONAL_NRT']),
      rec(2026, 10, 120, ['PROVISIONAL_NRT', 'WIDE_INTERVAL']),
      rec(2026, 11, null, ['OUTAGE', 'PROVISIONAL_NRT']),
    ]
    expect(latestDeterminableMonth(series, { year: 2026, month: 11 })).toEqual({ year: 2026, month: 10 })
  })

  it('counts a provisional month that has an estimate', () => {
    expect(latestDeterminableMonth([rec(2026, 3, 5, ['PROVISIONAL_NRT'])], null)).toEqual({ year: 2026, month: 3 })
  })

  it('skips a month with an OUTAGE code even when it has an estimate', () => {
    const series = [rec(2020, 1, 10), rec(2020, 2, 12, ['OUTAGE'])]
    expect(latestDeterminableMonth(series, null)).toEqual({ year: 2020, month: 1 })
  })

  it('skips a month with no estimate and no outage code', () => {
    const series = [rec(2020, 1, 10), rec(2020, 2, null, ['INSUFFICIENT_BASELINE'])]
    expect(latestDeterminableMonth(series, null)).toEqual({ year: 2020, month: 1 })
  })

  it('does not depend on the order of the records, and compares years before months', () => {
    const series = [rec(2021, 2, 1), rec(2019, 12, 1), rec(2021, 1, 1), rec(2020, 11, 1)]
    expect(latestDeterminableMonth(series, null)).toEqual({ year: 2021, month: 2 })
  })

  it('falls back when no month qualifies, or the series is empty', () => {
    const fallback = { year: 2026, month: 11 }
    expect(latestDeterminableMonth([rec(2026, 1, null, ['OUTAGE'])], fallback)).toEqual(fallback)
    expect(latestDeterminableMonth([], fallback)).toEqual(fallback)
    expect(latestDeterminableMonth([], null)).toBeNull()
  })
})
