import { describe, expect, it } from 'vitest'
import { monthRange } from '../../state/months.ts'
import {
  applyKeyAction,
  clampToRange,
  indexOfMonth,
  keyAction,
  monthStatus,
  parseMonthInput,
  shiftMonth,
  shiftYear,
  yearTicks,
  yearsOf,
} from './monthPicker.ts'

// SYNTHETIC test list with the shape of the record (2002-07 to 2026-11, the last four months provisional): the real list comes from
// the metadata at run time; nothing here is shown in the app.
const months = monthRange('2002-07', '2026-11', ['2026-08', '2026-09', '2026-10', '2026-11'])

describe('month picker logic (T-087)', () => {
  it('lists every year of the record and marks the months outside it', () => {
    const years = yearsOf(months)
    expect(years[0]).toBe(2002)
    expect(years[years.length - 1]).toBe(2026)
    expect(years).toHaveLength(25)
    expect(monthStatus(months, { year: 2002, month: 6 })).toBe('outside')
    expect(monthStatus(months, { year: 2002, month: 7 })).toBe('available')
    expect(monthStatus(months, { year: 2026, month: 7 })).toBe('available')
    expect(monthStatus(months, { year: 2026, month: 8 })).toBe('provisional')
    expect(monthStatus(months, { year: 2026, month: 11 })).toBe('provisional')
    expect(monthStatus(months, { year: 2026, month: 12 })).toBe('outside')
  })

  it('every month of the record is reachable in at most 2 interactions: the picker has a button for each', () => {
    // open the picker (1), press the month (2): the picker lists every year, so every listed month has exactly one button
    const reachable = new Set<string>()
    for (const year of yearsOf(months)) {
      for (let month = 1; month <= 12; month += 1) {
        if (monthStatus(months, { year, month }) !== 'outside') reachable.add(`${year}-${month}`)
      }
    }
    expect(reachable.size).toBe(months.length)
    expect(months).toHaveLength(293)
  })

  it('clamps to the first and last month of the record', () => {
    expect(clampToRange(months, { year: 1999, month: 1 })).toMatchObject({ year: 2002, month: 7 })
    expect(clampToRange(months, { year: 2002, month: 7 })).toMatchObject({ year: 2002, month: 7 })
    expect(clampToRange(months, { year: 2019, month: 12 })).toMatchObject({ year: 2019, month: 12 })
    expect(clampToRange(months, { year: 2030, month: 5 })).toMatchObject({ year: 2026, month: 11 })
    expect(clampToRange([], { year: 2019, month: 12 })).toBeNull()
  })

  it('parses a typed month and rejects everything else, without guessing', () => {
    expect(parseMonthInput('2019-12')).toEqual({ year: 2019, month: 12 })
    expect(parseMonthInput(' 2019-1 ')).toEqual({ year: 2019, month: 1 })
    expect(parseMonthInput('2019/12')).toEqual({ year: 2019, month: 12 })
    expect(parseMonthInput('12/2019')).toEqual({ year: 2019, month: 12 })
    for (const bad of ['', '2019', '2019-13', '2019-00', 'Dec 2019', '19-12', '2019-12-01', '2019-1x']) expect(parseMonthInput(bad)).toBeNull()
  })

  it('moves one year with the month kept, and stays inside the record at the ends', () => {
    expect(shiftYear(months, { year: 2019, month: 12 }, -1)).toMatchObject({ year: 2018, month: 12 })
    expect(shiftYear(months, { year: 2019, month: 12 }, 1)).toMatchObject({ year: 2020, month: 12 })
    expect(shiftYear(months, { year: 2003, month: 3 }, -1)).toMatchObject({ year: 2002, month: 7 }) // 2002-03 is before the record
    expect(shiftYear(months, { year: 2026, month: 1 }, 1)).toMatchObject({ year: 2026, month: 11 })
    expect(shiftMonth(months, { year: 2002, month: 7 }, -1)).toBeNull()
    expect(shiftMonth(months, { year: 2026, month: 11 }, 1)).toBeNull()
    expect(shiftMonth(months, { year: 2019, month: 12 }, 1)).toMatchObject({ year: 2020, month: 1 })
  })

  it('maps the keys to the actions of the Lead: arrows months, Page keys years, Home and End the ends', () => {
    expect(keyAction('ArrowLeft')).toEqual({ type: 'month', delta: -1 })
    expect(keyAction('ArrowRight')).toEqual({ type: 'month', delta: 1 })
    expect(keyAction('PageUp')).toEqual({ type: 'year', delta: 1 })
    expect(keyAction('PageDown')).toEqual({ type: 'year', delta: -1 })
    expect(keyAction('Home')).toEqual({ type: 'first' })
    expect(keyAction('End')).toEqual({ type: 'last' })
    expect(keyAction('a')).toBeNull()
    const from = { year: 2019, month: 12 }
    expect(applyKeyAction(months, from, { type: 'month', delta: -1 })).toMatchObject({ year: 2019, month: 11 })
    expect(applyKeyAction(months, from, { type: 'year', delta: 1 })).toMatchObject({ year: 2020, month: 12 })
    expect(applyKeyAction(months, from, { type: 'first' })).toMatchObject({ year: 2002, month: 7 })
    expect(applyKeyAction(months, from, { type: 'last' })).toMatchObject({ year: 2026, month: 11 })
    // nowhere to go: a year step at the last month, a month step at the first
    expect(applyKeyAction(months, { year: 2026, month: 11 }, { type: 'year', delta: 1 })).toBeNull()
    expect(applyKeyAction(months, { year: 2002, month: 7 }, { type: 'month', delta: -1 })).toBeNull()
  })

  it('places a tick at the first month of every year and labels every fifth year', () => {
    const ticks = yearTicks(months)
    expect(ticks[0]).toMatchObject({ year: 2002, percent: 0, labelled: false })
    expect(ticks.filter((t) => t.labelled).map((t) => t.year)).toEqual([2005, 2010, 2015, 2020, 2025])
    const t2020 = ticks.find((t) => t.year === 2020)
    expect(t2020?.percent).toBeCloseTo((indexOfMonth(months, { year: 2020, month: 1 }) / (months.length - 1)) * 100, 9)
    expect(ticks.every((t, i) => i === 0 || t.percent > (ticks[i - 1]?.percent ?? 0))).toBe(true)
    expect(yearTicks([])).toEqual([])
  })
})
