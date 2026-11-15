/** One month of the sparkline. Null values are missing data: a gap, never zero. */
export interface SparkPoint {
  year: number
  month: number
  estimate: number | null
  p25: number | null
  p75: number | null
}

export interface YearMonth {
  year: number
  month: number
}

const idx = (m: YearMonth) => m.year * 12 + (m.month - 1)
const fromIdx = (i: number): YearMonth => ({ year: Math.floor(i / 12), month: (i % 12) + 1 })

export const SPARK_MONTHS = 12

/**
 * The 12 consecutive months shown: they end 3 months after the selected one (or at the latest
 * month), and never start before the first month. Fewer than 12 only if the record is shorter.
 */
export function sparkWindow(selected: YearMonth, first: YearMonth, latest: YearMonth): YearMonth[] {
  let end = Math.min(idx(latest), idx(selected) + 3)
  let start = end - (SPARK_MONTHS - 1)
  if (start < idx(first)) {
    start = idx(first)
    end = Math.min(idx(latest), start + SPARK_MONTHS - 1)
  }
  const out: YearMonth[] = []
  for (let i = start; i <= end; i++) out.push(fromIdx(i))
  return out
}

export interface SparkGeometry {
  /** SVG path data of each unbroken run of the line. */
  lines: string[]
  /** Runs of a single month, drawn as dots (a line needs two points). */
  dots: { x: number; y: number }[]
  /** One rectangle per month with a normal range: the band behind the line. */
  bands: { x: number; y: number; w: number; h: number }[]
  marker: { x: number; y: number } | null
  markerX: number | null
  yMax: number
}

const round = (v: number) => Math.round(v * 100) / 100

/** Draws the points into a width x height box with `pad` around it. Values are scaled from 0 to the largest shown. */
export function buildSpark(
  points: readonly SparkPoint[],
  selectedIndex: number | null,
  width: number,
  height: number,
  pad = 4,
): SparkGeometry {
  const n = points.length
  const values = points.flatMap((p) => [p.estimate, p.p75]).filter((v): v is number => v !== null)
  const yMax = values.length === 0 ? 1 : Math.max(...values, Number.EPSILON)
  const step = n > 1 ? (width - 2 * pad) / (n - 1) : 0
  const x = (i: number) => (n > 1 ? pad + i * step : width / 2)
  const y = (v: number) => round(height - pad - (Math.max(v, 0) / yMax) * (height - 2 * pad))

  const lines: string[] = []
  const dots: { x: number; y: number }[] = []
  let run: { x: number; y: number }[] = []
  const flush = () => {
    if (run.length >= 2) lines.push(run.map((p, k) => `${k === 0 ? 'M' : 'L'}${p.x} ${p.y}`).join(' '))
    else if (run.length === 1 && run[0] !== undefined) dots.push(run[0])
    run = []
  }
  points.forEach((p, i) => {
    if (p.estimate === null) flush()
    else run.push({ x: round(x(i)), y: y(p.estimate) })
  })
  flush()

  const half = n > 1 ? step / 2 : width / 2
  const bands = points.flatMap((p, i) => {
    if (p.p25 === null || p.p75 === null) return []
    const left = Math.max(0, x(i) - half)
    const right = Math.min(width, x(i) + half)
    const top = y(p.p75)
    return [{ x: round(left), y: top, w: round(right - left), h: Math.max(round(y(p.p25) - top), 1) }]
  })

  const sel = selectedIndex === null ? undefined : points[selectedIndex]
  const marker =
    selectedIndex !== null && sel !== undefined && sel.estimate !== null ? { x: round(x(selectedIndex)), y: y(sel.estimate) } : null
  return { lines, dots, bands, marker, markerX: selectedIndex === null ? null : round(x(selectedIndex)), yMax }
}

export function countGaps(points: readonly SparkPoint[]): number {
  return points.filter((p) => p.estimate === null).length
}
