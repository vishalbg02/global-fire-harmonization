import { MONTH_ABBR, NO_RECORD, OUTSIDE_RECORD } from '../../content/calendar.ts'
import type { ValueMode } from '../../state/selection.ts'
import { formatPctOfNormal } from '../map/format.ts'
import type { CalendarCell, CalendarRow } from './grid.ts'
import { cellVisual, toCss } from './scales.ts'
import { cellAriaLabel, provisionalNote } from './text.ts'

interface Props {
  rows: readonly CalendarRow[]
  mode: ValueMode
  maxActivity: number
  selected: { year: number; month: number } | null
  areaName: string
  onSelectMonth: (year: number, month: number) => void
}

function valueText(cell: CalendarCell, mode: ValueMode): string {
  const r = cell.record
  if (r === null) return ''
  if (mode === 'pct') return formatPctOfNormal(r.pct_of_normal).replace(' of normal', '')
  return r.estimate === null ? 'no data' : r.estimate.toFixed(1)
}

/** The same data as the heatmap, as a table: keyboard-operable and readable by screen readers. */
export function CalendarTable({ rows, mode, maxActivity, selected, areaName, onSelectMonth }: Props) {
  return (
    <div className="calendar-table-wrap">
      <table className="calendar-table">
        <caption>Monthly satellite-detected fire activity for {areaName}</caption>
        <thead>
          <tr>
            <th scope="col">Year</th>
            {MONTH_ABBR.map((m) => (
              <th key={m} scope="col">
                {m}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row.year}>
              <th scope="row">{row.year}</th>
              {row.cells.map((cell) => {
                const key = `${cell.year}-${cell.month}`
                if (cell.kind === 'outside') {
                  return (
                    <td key={key} className="cal-outside">
                      <span aria-hidden="true">–</span>
                      <span className="visually-hidden">{OUTSIDE_RECORD}</span>
                    </td>
                  )
                }
                if (cell.kind === 'no-record' || cell.record === null) {
                  return (
                    <td key={key} className="cal-nodata">
                      {NO_RECORD.toLowerCase()}
                    </td>
                  )
                }
                const visual = cellVisual(cell.record, mode, maxActivity)
                const isSelected = selected?.year === cell.year && selected.month === cell.month
                const provisional = provisionalNote(cell)
                return (
                  <td key={key}>
                    <button
                      type="button"
                      className={`cal-cell${isSelected ? ' cal-selected' : ''}${provisional === null ? '' : ' cal-provisional'}`}
                      style={{ background: toCss(visual.color), color: toCss(visual.text) }}
                      aria-label={cellAriaLabel(cell)}
                      aria-pressed={isSelected}
                      onClick={() => onSelectMonth(cell.year, cell.month)}
                    >
                      <span aria-hidden="true">{visual.icon} </span>
                      {valueText(cell, mode)}
                      {provisional !== null && <span aria-hidden="true"> P</span>}
                    </button>
                  </td>
                )
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
