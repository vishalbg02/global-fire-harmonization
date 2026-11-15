import { describe, expect, it } from 'vitest'
import { MONTH_NAMES, annualSeries, compareSeries, coverage, coverageInArea, ordinal, rankInMonth, rankText, seasonProfile } from './compute.ts'
import type { EntityMonth } from '../../api/contract.ts'

// SYNTHETIC test values: they only exercise the arithmetic and are not results.
const rec = (year: number, month: number, estimate: number | null, raw = 10, level: 'SP' | 'NRT' = 'SP', pct: number | null = null) => ({
  year, month, estimate, raw_combined_cell_days: raw, data_level: level,
  baseline_p25: 10, baseline_median: 20, baseline_p75: 30, pct_of_normal: pct,
})

describe('annualSeries (SYNTHETIC values)', () => {
  it('sums the estimate and the raw count over the months that have an estimate, and marks partial years', () => {
    const records = [rec(2020, 1, 5, 7), rec(2020, 2, 6, 8), rec(2020, 3, null, 9), rec(2021, 1, 1, 2, 'NRT')]
    expect(annualSeries(records)).toEqual([
      { year: 2020, monthsUsed: 2, harmonizedSum: 11, rawSum: 15, partial: true, provisional: false },
      { year: 2021, monthsUsed: 1, harmonizedSum: 1, rawSum: 2, partial: true, provisional: true },
    ])
  })
  it('calls a year with 12 estimates complete', () => {
    const records = Array.from({ length: 12 }, (_, i) => rec(2019, i + 1, 1))
    expect(annualSeries(records)[0]).toMatchObject({ monthsUsed: 12, harmonizedSum: 12, partial: false })
  })
})

describe('seasonProfile (SYNTHETIC values)', () => {
  it('takes the band from the stored baseline and the selected year line from the estimates', () => {
    const records = [rec(2019, 3, 4), rec(2020, 3, 8), rec(2020, 4, null)]
    const p = seasonProfile(records, 2020)
    expect(p).toHaveLength(12)
    expect(p[2]).toEqual({ month: 3, p25: 10, median: 20, p75: 30, selected: 8 })
    expect(p[3].selected).toBeNull()
    expect(p[5]).toEqual({ month: 6, p25: null, median: null, p75: null, selected: null })
  })
})

describe('rankInMonth (SYNTHETIC values)', () => {
  const records = [rec(2010, 9, 50), rec(2011, 9, 70), rec(2012, 9, 70), rec(2013, 9, 10), rec(2015, 9, 90, 1, 'NRT'), rec(2014, 9, null), rec(2013, 8, 999)]
  it('ranks with competition ranking, states ties and the years without an estimate', () => {
    const r = rankInMonth(records, 2011, 9)
    expect(r).toMatchObject({ rank: 2, of: 5, tiedWith: [2012], missingYears: [2014] })
    expect(rankInMonth(records, 2015, 9)).toMatchObject({ rank: 1, provisional: true })
    expect(rankInMonth(records, 2013, 9)).toMatchObject({ rank: 5 })
  })
  it('returns null when the selected month has no estimate', () => {
    expect(rankInMonth(records, 2014, 9)).toBeNull()
    expect(rankInMonth(records, 2010, 5)).toBeNull()
  })
  it('writes the sentence', () => {
    const lines = rankText(rankInMonth(records, 2011, 9)!)
    expect(lines[0]).toBe('September 2011 is the 2nd highest September of the record (5 years with an estimate).')
    expect(lines).toContain('Tied with 2012: the same estimate.')
    expect(lines).toContain('No estimate for September in 2014.')
    expect(ordinal(1)).toBe('1st'); expect(ordinal(11)).toBe('11th'); expect(ordinal(22)).toBe('22nd'); expect(ordinal(103)).toBe('103rd')
    expect(MONTH_NAMES[8]).toBe('September')
  })
})

describe('coverage (SYNTHETIC cells)', () => {
  const cell = (lat: number, lon: number, verdict: string) => ({ lat_min: lat - 0.25, lat_max: lat + 0.25, lon_min: lon - 0.25, lon_max: lon + 0.25, verdict }) as never
  const cells = [cell(0, 0, 'ABOVE_NORMAL'), cell(0, 1, 'CANNOT_DETERMINE'), cell(0, 2, 'NO_DETECTED_ACTIVITY'), cell(10, 10, 'WITHIN_NORMAL')]
  it('counts the cells whose centre is inside the box, edges inclusive, and the determinable share', () => {
    expect(coverage(cells, [0, 0, 2, 0])).toEqual({ cells: 3, determinable: 2, share: 2 / 3, byVerdict: { ABOVE_NORMAL: 1, CANNOT_DETERMINE: 1, NO_DETECTED_ACTIVITY: 1 } })
  })
  it('uses the whole world without a box and returns null for an empty box', () => {
    expect(coverage(cells, null)).toMatchObject({ cells: 4, determinable: 3 })
    expect(coverage(cells, [50, 50, 60, 60])).toBeNull()
  })
})

describe('coverageInArea (SYNTHETIC cells and areas, T-090)', () => {
  const areas = {
    cell_id: ['a', 'b', 'c', 'd', 'e', 'f'],
    country_iso3: ['IDN', 'IDN', 'MYS', 'IND', null, 'IDN'],
    continent: ['AS', 'AS', 'AS', 'AS', null, 'AS'],
  }
  const month = [
    { cell_id: 'a', verdict: 'ABOVE_NORMAL' },
    { cell_id: 'b', verdict: 'CANNOT_DETERMINE' },
    { cell_id: 'c', verdict: 'WITHIN_NORMAL' },
    { cell_id: 'd', verdict: 'CANNOT_DETERMINE' },
    { cell_id: 'e', verdict: 'WITHIN_NORMAL' },
    // cell f is not in this month: only the cells of the month are counted
  ] as never[]
  it('counts only the cells stored for the country, never a neighbour (the bounding-box figure counted them)', () => {
    expect(coverageInArea(month, areas, 'COUNTRY', 'IDN')).toEqual({ cells: 2, determinable: 1, share: 0.5, byVerdict: { ABOVE_NORMAL: 1, CANNOT_DETERMINE: 1 } })
    expect(coverageInArea(month, areas, 'COUNTRY', 'MYS')).toMatchObject({ cells: 1, determinable: 1, share: 1 })
  })
  it('counts a continent by the continent stored for each cell, and leaves out cells with none', () => {
    expect(coverageInArea(month, areas, 'CONTINENT', 'AS')).toMatchObject({ cells: 4, determinable: 2 })
  })
  it('is null for an area with no cell in the month', () => {
    expect(coverageInArea(month, areas, 'COUNTRY', 'BRA')).toBeNull()
    expect(coverageInArea([], areas, 'COUNTRY', 'IDN')).toBeNull()
  })
})

describe('compareSeries (SYNTHETIC values)', () => {
  it('aligns by month and keeps a missing value as null, never 0', () => {
    const a = [rec(2020, 1, 1, 1, 'SP', 150), rec(2020, 2, 1, 1, 'SP', null)] as unknown as EntityMonth[]
    const b = [rec(2020, 1, 1, 1, 'SP', 80)] as unknown as EntityMonth[]
    expect(compareSeries(a, b)).toEqual([{ label: '2020-01', a: 150, b: 80 }, { label: '2020-02', a: null, b: null }])
  })
})
