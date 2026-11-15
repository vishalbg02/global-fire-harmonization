import { useId } from 'react'
import type { EntityMonth } from '../../api/contract.ts'
import { SPARK_CAPTION_SHORT } from '../../content/answer.ts'
import { SPARK_NAME, SPARK_NO_DATA, SPARK_NO_RANGE, SPARK_TEXT, SPARK_UNIT } from '../../content/ui.ts'
import { monthKey, monthLabel } from '../../state/months.ts'
import { oneDecimal } from '../map/format.ts'
import { buildSpark, countGaps, sparkWindow } from './sparkline.ts'
import type { SparkPoint, YearMonth } from './sparkline.ts'

const W = 320
const H = 60

interface Props {
  records: readonly EntityMonth[]
  selected: YearMonth
  first: YearMonth
  latest: YearMonth
  areaName: string
}

/**
 * The 12-month estimate with the normal range (the baseline 25th to 75th percentile of each
 * calendar month) as a band behind the line. A month without data is a gap in the line, never 0.
 * The same numbers are in a text equivalent and in a table for screen readers.
 */
export function Sparkline({ records, selected, first, latest, areaName }: Props) {
  const id = useId()
  const byMonth = new Map(records.map((r) => [monthKey(r.year, r.month), r]))
  const window = sparkWindow(selected, first, latest)
  const points: SparkPoint[] = window.map((m) => {
    const r = byMonth.get(monthKey(m.year, m.month))
    return {
      year: m.year,
      month: m.month,
      estimate: r?.estimate ?? null,
      p25: r?.baseline_p25 ?? null,
      p75: r?.baseline_p75 ?? null,
    }
  })
  const selectedIndex = window.findIndex((m) => m.year === selected.year && m.month === selected.month)
  const geo = buildSpark(points, selectedIndex < 0 ? null : selectedIndex, W, H)
  const firstLabel = window[0] === undefined ? '' : monthLabel(window[0])
  const lastLabel = window[window.length - 1] === undefined ? '' : monthLabel(window[window.length - 1]!)
  const sel = selectedIndex < 0 ? undefined : points[selectedIndex]
  const text = SPARK_TEXT({
    first: firstLabel,
    last: lastLabel,
    selected: monthLabel(selected),
    estimate: sel?.estimate == null ? SPARK_NO_DATA : oneDecimal(sel.estimate),
    range: sel?.p25 == null || sel.p75 == null ? SPARK_NO_RANGE : `${oneDecimal(sel.p25)} to ${oneDecimal(sel.p75)}`,
    gaps: countGaps(points),
    months: points.length,
  })
  return (
    <figure className="spark" aria-labelledby={`${id}-name`}>
      <svg viewBox={`0 0 ${W} ${H}`} role="img" aria-labelledby={`${id}-name ${id}-text`} className="spark-svg">
        <title id={`${id}-name`}>{SPARK_NAME(areaName)}</title>
        <desc id={`${id}-text`}>{text}</desc>
        {geo.bands.map((b, i) => (
          <rect key={i} x={b.x} y={b.y} width={b.w} height={b.h} className="spark-band" />
        ))}
        {geo.markerX !== null && <line x1={geo.markerX} x2={geo.markerX} y1={2} y2={H - 2} className="spark-guide" />}
        {geo.lines.map((d, i) => (
          <path key={i} d={d} className="spark-line" fill="none" />
        ))}
        {geo.dots.map((d, i) => (
          <circle key={i} cx={d.x} cy={d.y} r={2} className="spark-dot" />
        ))}
        {geo.marker !== null && <circle cx={geo.marker.x} cy={geo.marker.y} r={4.5} className="spark-marker" />}
      </svg>
      {/* The unit is written once, under the interval bar above; the hidden table below repeats it. */}
      <figcaption>
        <span className="spark-note">{SPARK_CAPTION_SHORT(firstLabel, lastLabel, monthLabel(selected))}</span>
      </figcaption>
      <table className="visually-hidden">
        <caption>{`${SPARK_NAME(areaName)} (${SPARK_UNIT})`}</caption>
        <thead>
          <tr>
            <th scope="col">Month</th>
            <th scope="col">Estimate</th>
            <th scope="col">Normal range</th>
          </tr>
        </thead>
        <tbody>
          {points.map((p) => (
            <tr key={`${p.year}-${p.month}`}>
              <th scope="row">{monthLabel(p)}</th>
              <td>{p.estimate === null ? SPARK_NO_DATA : oneDecimal(p.estimate)}</td>
              <td>{p.p25 === null || p.p75 === null ? SPARK_NO_RANGE : `${oneDecimal(p.p25)} to ${oneDecimal(p.p75)}`}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </figure>
  )
}
