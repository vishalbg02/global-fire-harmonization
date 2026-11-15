/** Pure logic of the month picker (T-087): no React, no DOM. Months come from the metadata through `MonthOption` lists. */
import type { MonthOption } from '../../state/months.ts'

export interface YearMonth {
  year: number
  month: number
}

const key = (m: YearMonth) => m.year * 12 + (m.month - 1)

/** Index of a month in the list, or -1. */
export function indexOfMonth(months: readonly MonthOption[], target: YearMonth): number {
  return months.findIndex((m) => m.year === target.year && m.month === target.month)
}

/** The listed month closest to `target` (the first or last month when it lies outside the record), or null for an empty list. */
export function clampToRange(months: readonly MonthOption[], target: YearMonth): MonthOption | null {
  const first = months[0]
  const last = months[months.length - 1]
  if (first === undefined || last === undefined) return null
  if (key(target) <= key(first)) return first
  if (key(target) >= key(last)) return last
  return months.find((m) => key(m) >= key(target)) ?? last
}

export type MonthStatus = 'available' | 'provisional' | 'outside'

/** Whether a month is in the record, and whether it is provisional (near-real-time). */
export function monthStatus(months: readonly MonthOption[], target: YearMonth): MonthStatus {
  const i = indexOfMonth(months, target)
  if (i < 0) return 'outside'
  return months[i]?.provisional === true ? 'provisional' : 'available'
}

/** Every year of the record, ascending. */
export function yearsOf(months: readonly MonthOption[]): number[] {
  const years: number[] = []
  for (const m of months) if (years[years.length - 1] !== m.year) years.push(m.year)
  return years
}

/** The same month one year earlier or later, moved to the nearest month of the record (the first or last month at the ends). */
export function shiftYear(months: readonly MonthOption[], from: YearMonth, delta: -1 | 1): MonthOption | null {
  return clampToRange(months, { year: from.year + delta, month: from.month })
}

/** The month `delta` places away in the list, or null at the ends. */
export function shiftMonth(months: readonly MonthOption[], from: YearMonth, delta: -1 | 1): MonthOption | null {
  const i = indexOfMonth(months, from)
  return i < 0 ? null : (months[i + delta] ?? null)
}

/** Accepts `2019-12`, `2019-1`, `2019/12`, `2019 12` and `12/2019`; null for anything else (no guessing). */
export function parseMonthInput(text: string): YearMonth | null {
  const t = text.trim()
  const ym = /^(\d{4})[-/ ](\d{1,2})$/.exec(t)
  const my = /^(\d{1,2})\/(\d{4})$/.exec(t)
  const year = ym ? Number(ym[1]) : my ? Number(my[2]) : NaN
  const month = ym ? Number(ym[2]) : my ? Number(my[1]) : NaN
  if (!Number.isInteger(year) || !Number.isInteger(month) || month < 1 || month > 12) return null
  return { year, month }
}

export type PickerKeyAction =
  | { type: 'month'; delta: -1 | 1 }
  | { type: 'year'; delta: -1 | 1 }
  | { type: 'first' }
  | { type: 'last' }

/** The action of a key on the month control: arrows move months, PageUp and PageDown years, Home and End the first and last month. */
export function keyAction(k: string): PickerKeyAction | null {
  switch (k) {
    case 'ArrowLeft':
      return { type: 'month', delta: -1 }
    case 'ArrowRight':
      return { type: 'month', delta: 1 }
    case 'PageUp':
      return { type: 'year', delta: 1 }
    case 'PageDown':
      return { type: 'year', delta: -1 }
    case 'Home':
      return { type: 'first' }
    case 'End':
      return { type: 'last' }
    default:
      return null
  }
}

/** The month a key action leads to from `from`; null when there is nowhere to go. */
export function applyKeyAction(months: readonly MonthOption[], from: YearMonth, action: PickerKeyAction): MonthOption | null {
  switch (action.type) {
    case 'month':
      return shiftMonth(months, from, action.delta)
    case 'year': {
      const to = shiftYear(months, from, action.delta)
      return to !== null && (to.year !== from.year || to.month !== from.month) ? to : null
    }
    case 'first':
      return months[0] ?? null
    case 'last':
      return months[months.length - 1] ?? null
  }
}

export interface YearTick {
  year: number
  /** Position along the slider in percent (0 to 100), at the January of the year (the first month for the first year). */
  percent: number
  /** Labelled ticks are every `labelEvery` years; the others are plain marks. */
  labelled: boolean
}

/** Year ticks under the slider: a mark at the first month of every year, labelled every `labelEvery` years (2005, 2010, ...). */
export function yearTicks(months: readonly MonthOption[], labelEvery = 5): YearTick[] {
  const last = months.length - 1
  if (last < 1) return []
  const ticks: YearTick[] = []
  months.forEach((m, i) => {
    if (m.month === 1 || i === 0) ticks.push({ year: m.year, percent: (i / last) * 100, labelled: m.year % labelEvery === 0 })
  })
  return ticks
}
