import { BAR_INTERVAL_MISSING, BAR_NOT_AVAILABLE, BAR_RANGE, PCT_UNIT } from '../../content/answer.ts'
import { NO_DATA, formatPctOfNormal, oneDecimal } from '../map/format.ts'
import type { IntervalValues } from './intervalBar.ts'

/** "more than 99% likely above normal" gets a capital letter. */
export const sentence = (s: string) => s.charAt(0).toUpperCase() + s.slice(1)

/**
 * The big number and its quieter unit, split from `formatPctOfNormal` (so the card shows exactly what the helper
 * writes: the stored % of normal, rounded to a whole number). Null when the stored value is missing.
 */
export function pctParts(pct: number | null): { value: string; unit: string } | null {
  if (pct === null) return null
  const text = formatPctOfNormal(pct)
  const at = text.lastIndexOf(PCT_UNIT)
  return at < 0 ? { value: text, unit: '' } : { value: text.slice(0, at), unit: PCT_UNIT }
}

export interface IntervalTexts {
  estimate: string
  interval: string
  normal: string
  median: string
}

/**
 * The printed values of the interval bar: the stored values with one decimal (`oneDecimal`), never a computed one.
 * A missing estimate reads "no data"; an estimate without its interval reads "interval not available", as in
 * `formatEstimate`; a missing normal range or median reads "not available", as in the sparkline.
 */
export function intervalTexts(v: IntervalValues): IntervalTexts {
  const range = (a: number | null, b: number | null) => (a === null || b === null ? null : BAR_RANGE(oneDecimal(a), oneDecimal(b)))
  return {
    estimate: v.estimate === null ? NO_DATA : oneDecimal(v.estimate),
    interval: range(v.low, v.high) ?? (v.estimate === null ? NO_DATA : BAR_INTERVAL_MISSING),
    normal: range(v.p25, v.p75) ?? BAR_NOT_AVAILABLE,
    median: v.median === null ? BAR_NOT_AVAILABLE : oneDecimal(v.median),
  }
}
