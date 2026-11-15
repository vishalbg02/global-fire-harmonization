/**
 * Pure geometry of the timeline scrubber (T-093): where a month sits on the strip, which years are ticked and labelled
 * for a width, the provisional and unavailable spans, the satellite-join marks, the gaps of the background line and the
 * snapping of a pointer to a month. No React, no DOM. Positions are fractions of the strip (0 = the first month of the
 * record, 1 = the latest); nothing here is ever printed as a number.
 */
import type { EntityMonth } from '../../api/contract.ts'
import { SATELLITE_TIMELINE } from '../../content/witnessTimeline.ts'
import type { MonthOption } from '../../state/months.ts'
import { nextPlayIndex, playStartIndex } from '../map/playback.ts'

export interface YearMonth {
  year: number
  month: number
}

/** A month as one integer (months since year 0), so months can be compared and subtracted. */
export const monthIndex = (m: YearMonth): number => m.year * 12 + (m.month - 1)

/** The month of a month index. */
export const fromIndex = (k: number): YearMonth => ({ year: Math.floor(k / 12), month: (k % 12) + 1 })

/** The month of an ISO date or "YYYY-MM" string ("2012-01-20" is January 2012). */
export function monthOfIso(iso: string): YearMonth {
  return { year: Number(iso.slice(0, 4)), month: Number(iso.slice(5, 7)) }
}

/** The extent of the strip: the first and the latest month of the record, as month indexes. */
export interface Range {
  first: number
  last: number
}

export function rangeOf(months: readonly YearMonth[]): Range | null {
  const a = months[0]
  const b = months[months.length - 1]
  return a === undefined || b === undefined ? null : { first: monthIndex(a), last: monthIndex(b) }
}

/** Number of month steps along the strip (one less than the number of months). */
const steps = (r: Range) => Math.max(r.last - r.first, 1)

/** Position of a month on the strip, 0 for the first month and 1 for the latest, clamped to the strip. */
export function fractionOf(r: Range, m: YearMonth): number {
  return Math.min(1, Math.max(0, (monthIndex(m) - r.first) / steps(r)))
}

/** The month of the record nearest to a position on the strip (snapped to whole months, clamped to the record). */
export function monthAtFraction(r: Range, f: number): YearMonth {
  const k = r.first + Math.round(Math.min(1, Math.max(0, f)) * steps(r))
  return fromIndex(k)
}

/** Half the width of one month on the strip, as a fraction (a month covers its point plus or minus this). */
export const halfMonth = (r: Range): number => 0.5 / steps(r)

// ---- Ticks and labels ----

export interface YearTick {
  year: number
  /** Position on the strip: January of the year, or the first month of the record for the first year. */
  f: number
  labelled: boolean
  /** How the label is anchored to its tick, so the end labels stay inside the strip. */
  align: 'start' | 'middle' | 'end'
}

/** Width in px a year label takes (four Mono digits at 12 px), and the least space between two labels. */
export const LABEL_W = 30
export const LABEL_GAP = 8
/** Width in px a label needs along the strip, gap included: decides the label step. */
export const LABEL_PX = LABEL_W + 14

/** Every how many years a label is drawn for a strip `widthPx` wide: 2, 4 or 8, the smallest that leaves room. */
export function labelStep(r: Range, widthPx: number): number {
  const pxPerYear = (widthPx * 12) / steps(r)
  for (const step of [2, 4, 8]) if (pxPerYear * step >= LABEL_PX) return step
  return 16
}

/** Left and right edges in px of a label anchored at `x` on a strip `widthPx` wide. */
function labelBox(x: number, align: YearTick['align']): [number, number] {
  return align === 'start' ? [x, x + LABEL_W] : align === 'end' ? [x - LABEL_W, x] : [x - LABEL_W / 2, x + LABEL_W / 2]
}

/**
 * A tick for every year of the record; labels every `labelStep` years counted from the first year. The first and the
 * latest year are always labelled; a label in between that would come closer than `LABEL_GAP` to a kept one is dropped.
 */
export function yearTicks(r: Range, widthPx: number): YearTick[] {
  const step = labelStep(r, widthPx)
  const firstYear = fromIndex(r.first).year
  const lastYear = fromIndex(r.last).year
  const ticks: YearTick[] = []
  for (let year = firstYear; year <= lastYear; year += 1) {
    const f = year === firstYear ? 0 : fractionOf(r, { year, month: 1 })
    const x = f * widthPx
    const align = x - LABEL_W / 2 < 0 ? 'start' : x + LABEL_W / 2 > widthPx ? 'end' : 'middle'
    ticks.push({ year, f, labelled: year === firstYear || year === lastYear || (year - firstYear) % step === 0, align })
  }
  const last = ticks[ticks.length - 1]
  const lastLeft = last === undefined ? Infinity : labelBox(last.f * widthPx, last.align)[0]
  let keptRight = -Infinity
  for (const t of ticks) {
    if (!t.labelled) continue
    const [left, right] = labelBox(t.f * widthPx, t.align)
    const ends = t.year === firstYear || t === last
    if (!ends && (left < keptRight + LABEL_GAP || right > lastLeft - LABEL_GAP)) t.labelled = false
    else keptRight = right
  }
  return ticks
}

// ---- Spans (provisional, no map) ----

export interface Span {
  /** Left and right edges on the strip; a span covers whole months (half a month either side of the points). */
  from: number
  to: number
}

/** The contiguous runs of the months in `keys` (month indexes) inside the record, as spans on the strip. */
export function spansOf(r: Range, keys: Iterable<number>): Span[] {
  const sorted = [...new Set(keys)].filter((k) => k >= r.first && k <= r.last).sort((a, b) => a - b)
  const spans: Span[] = []
  const h = halfMonth(r)
  let start: number | null = null
  let prev = 0
  const close = () => {
    if (start === null) return
    spans.push({
      from: Math.max(0, (start - r.first) / steps(r) - h),
      to: Math.min(1, (prev - r.first) / steps(r) + h),
    })
  }
  for (const k of sorted) {
    if (start !== null && k === prev + 1) prev = k
    else {
      close()
      start = k
      prev = k
    }
  }
  close()
  return spans
}

/** The provisional months ("YYYY-MM", from the metadata) as spans. */
export function provisionalSpans(r: Range, provisional: readonly string[]): Span[] {
  return spansOf(r, provisional.map((ym) => monthIndex(monthOfIso(ym))))
}

/** The months of the record that have no map (an offline copy with maps for some months only), as spans. */
export function unavailableSpans(r: Range, available: readonly YearMonth[]): Span[] {
  const have = new Set(available.map(monthIndex))
  const missing: number[] = []
  for (let k = r.first; k <= r.last; k += 1) if (!have.has(k)) missing.push(k)
  return spansOf(r, missing)
}

// ---- Satellite joins ----

/** The satellites whose start is marked on the strip: the two VIIRS instruments the harmonization adds to Aqua. */
export const JOIN_WITNESSES = ['SNPP_VIIRS', 'NOAA20_VIIRS'] as const

export interface JoinMark {
  label: string
  /** The label without the instrument name, for narrow strips ("S-NPP"). */
  short: string
  month: YearMonth
  f: number
}

/** Where the VIIRS satellites join the record, with the dates of `content/witnessTimeline.ts` (never typed here). */
export function joinMarks(r: Range): JoinMark[] {
  return JOIN_WITNESSES.flatMap((w) => {
    const entry = SATELLITE_TIMELINE.find((e) => e.witness === w)
    if (entry === undefined) return []
    const month = monthOfIso(entry.start)
    const k = monthIndex(month)
    if (k < r.first || k > r.last) return []
    return [{ label: entry.label, short: entry.label.replace(/ VIIRS$/, ''), month, f: fractionOf(r, month) }]
  })
}

// ---- The background line ----

export type LineField = 'estimate' | 'raw_combined_cell_days'

/** One point of the line: position on the strip and height (0 = the bottom, 1 = the series' highest value). */
export interface LinePoint {
  f: number
  h: number
}

/**
 * The series as runs of consecutive months that have a value. A null value, or a month with no record, ends a run:
 * the line has a gap there and is never interpolated or drawn at zero. The vertical scale is linear from zero to the
 * highest value of the drawn field, one scale for the whole record (geometry only, never printed).
 */
export function lineSegments(r: Range, series: readonly EntityMonth[] | undefined, field: LineField): LinePoint[][] {
  if (series === undefined || series.length === 0) return []
  const byMonth = new Map<number, number>()
  for (const rec of series) {
    const v = rec[field]
    if (typeof v === 'number' && Number.isFinite(v)) byMonth.set(rec.year * 12 + (rec.month - 1), v)
  }
  let max = 0
  for (const v of byMonth.values()) if (v > max) max = v
  const segments: LinePoint[][] = []
  let run: LinePoint[] = []
  for (let k = r.first; k <= r.last; k += 1) {
    const v = byMonth.get(k)
    if (v === undefined) {
      if (run.length > 0) segments.push(run)
      run = []
    } else run.push({ f: (k - r.first) / steps(r), h: max > 0 ? v / max : 0 })
  }
  if (run.length > 0) segments.push(run)
  return segments
}

// ---- Snapping and the keys ----

/** The month of `available` nearest to `target` (the earlier one on a tie); null for an empty list. */
export function snapToAvailable(available: readonly YearMonth[], target: YearMonth): YearMonth | null {
  const t = monthIndex(target)
  let best: YearMonth | null = null
  let bestD = Infinity
  for (const m of available) {
    const d = Math.abs(monthIndex(m) - t)
    if (d < bestD) {
      best = m
      bestD = d
    }
  }
  return best
}

/** The available months just before and just after a month (for a month that has no map). */
export function neighbours(available: readonly YearMonth[], target: YearMonth): { before: YearMonth | null; after: YearMonth | null } {
  const t = monthIndex(target)
  let before: YearMonth | null = null
  let after: YearMonth | null = null
  for (const m of available) {
    const k = monthIndex(m)
    if (k < t) before = m
    else if (k > t && after === null) after = m
  }
  return { before, after }
}

/**
 * The month a key on the slider leads to: Left/Down one month back, Right/Up one month on, PageDown and PageUp a year,
 * Home and End the first and latest month. Only months of `available` are reached; a month that has no map steps to the
 * nearest map month on that side. Null for another key or when there is nowhere to go.
 */
export function sliderKeyTarget(available: readonly MonthOption[], value: YearMonth | null, key: string): YearMonth | null {
  const first = available[0]
  const last = available[available.length - 1]
  if (first === undefined || last === undefined) return null
  if (key === 'Home') return first
  if (key === 'End') return last
  if (value === null) return null
  const i = available.findIndex((m) => m.year === value.year && m.month === value.month)
  const month = key === 'ArrowLeft' || key === 'ArrowDown' ? -1 : key === 'ArrowRight' || key === 'ArrowUp' ? 1 : 0
  if (month !== 0) {
    if (i >= 0) return available[i + month] ?? null
    const { before, after } = neighbours(available, value)
    return month < 0 ? before : after
  }
  const year = key === 'PageUp' ? 1 : key === 'PageDown' ? -1 : 0
  if (year === 0) return null
  const to = snapToAvailable(available, { year: value.year + year, month: value.month })
  // Move only in the direction asked (the nearest month could be the current one, or on the other side).
  if (to === null || Math.sign(monthIndex(to) - monthIndex(value)) !== year) return null
  return to
}

// ---- The time-lapse ----

export type PlayStep = { type: 'idle' } | { type: 'stop' } | { type: 'go'; index: number } | { type: 'wait'; next: number }

/**
 * What the time-lapse does now, from the shared play state (App owns it; Space and the Play button flip it):
 * - not playing: nothing;
 * - playing under reduced motion, or with no month: stop at once (autoplay is off);
 * - just started on the latest month or a month without a map: go to the first month;
 * - otherwise wait one interval and show the next month, and stop after the latest.
 */
export function playStep(o: { playing: boolean; justStarted: boolean; reduced: boolean; index: number; count: number }): PlayStep {
  if (!o.playing) return { type: 'idle' }
  if (o.reduced || o.count === 0) return { type: 'stop' }
  if (o.justStarted) {
    const start = playStartIndex(o.index, o.count)
    if (start !== o.index) return { type: 'go', index: start }
  }
  const next = nextPlayIndex(o.index, o.count)
  return next === null ? { type: 'stop' } : { type: 'wait', next }
}
