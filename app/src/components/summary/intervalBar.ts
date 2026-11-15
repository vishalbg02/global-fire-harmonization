import type { EntityMonth } from '../../api/contract.ts'

/**
 * Geometry of the interval bar (T-093): where to draw the estimate, its 90% interval, the normal range (the baseline
 * 25th to 75th percentile) and the median on a horizontal line. Drawing only: these positions are never printed. The
 * printed numbers are the stored values, through `oneDecimal`, in IntervalBar.tsx.
 *
 * A null value is missing data: it is not drawn, and it never counts as zero.
 */

export interface IntervalValues {
  estimate: number | null
  low: number | null
  high: number | null
  p25: number | null
  p75: number | null
  median: number | null
}

/** The six stored fields the bar shows, by their contract names. */
export const intervalValues = (
  r: Pick<EntityMonth, 'estimate' | 'ci90_low' | 'ci90_high' | 'baseline_p25' | 'baseline_p75' | 'baseline_median'>,
): IntervalValues => ({
  estimate: r.estimate,
  low: r.ci90_low,
  high: r.ci90_high,
  p25: r.baseline_p25,
  p75: r.baseline_p75,
  median: r.baseline_median,
})

/** A horizontal run: left edge and width, in drawing units. */
export interface Span {
  x: number
  w: number
}

export interface IntervalGeometry {
  /** The value range the width stands for: from 0 (or the smallest value, if one is below 0) to the largest value. */
  domain: readonly [number, number]
  /** Where zero lies (a small tick, so the reader sees that the line starts at zero). */
  origin: number
  /** Centre of the estimate mark, or null when there is no estimate. */
  estimate: number | null
  /** The 90% interval, or null when either bound is missing. */
  interval: Span | null
  /** The normal range, or null when either percentile is missing. */
  band: Span | null
  /** The median tick, or null when there is no median. */
  median: number | null
}

/** A run is never drawn thinner than this, so a very narrow interval or band stays visible. */
export const MIN_SPAN = 2

const round = (v: number) => Math.round(v * 100) / 100
const finite = (v: number | null): v is number => v !== null && Number.isFinite(v)

/**
 * Places the values on a `width`-wide line with `pad` drawing units kept free at each end (so a mark at either end is
 * not cut). Returns null when there is nothing to draw (every value missing).
 */
export function intervalBar(v: IntervalValues, width: number, pad = 6): IntervalGeometry | null {
  const interval = finite(v.low) && finite(v.high) ? ([Math.min(v.low, v.high), Math.max(v.low, v.high)] as const) : null
  const band = finite(v.p25) && finite(v.p75) ? ([Math.min(v.p25, v.p75), Math.max(v.p25, v.p75)] as const) : null
  const estimate = finite(v.estimate) ? v.estimate : null
  const median = finite(v.median) ? v.median : null
  const values = [estimate, ...(interval ?? []), ...(band ?? []), median].filter(finite)
  if (values.length === 0) return null

  const lo = Math.min(0, ...values)
  const top = Math.max(...values)
  const hi = top > lo ? top : lo + 1
  const inner = Math.max(width - 2 * pad, 0)
  const x = (value: number) => round(pad + ((value - lo) / (hi - lo)) * inner)
  const span = ([a, b]: readonly [number, number]): Span => {
    const left = x(a)
    const right = x(b)
    if (right - left >= MIN_SPAN) return { x: left, w: round(right - left) }
    const centre = (left + right) / 2
    const start = Math.min(Math.max(centre - MIN_SPAN / 2, 0), Math.max(width - MIN_SPAN, 0))
    return { x: round(start), w: MIN_SPAN }
  }

  return {
    domain: [lo, hi],
    origin: x(0),
    estimate: estimate === null ? null : x(estimate),
    interval: interval === null ? null : span(interval),
    band: band === null ? null : span(band),
    median: median === null ? null : x(median),
  }
}
