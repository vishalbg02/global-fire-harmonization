import { ACTIVITY_UNITS, MONTH_ABBR, NO_RECORD, OUTSIDE_RECORD } from '../../content/calendar.ts'
import { REASON_CODE_SHORT } from '../../content/reasonCodes.ts'
import { VERDICT_PRESENTATION } from '../../content/verdicts.ts'
import type { Source } from '../../state/selection.ts'
import { formatEstimate, formatPctOfNormal, verdictProbability } from '../map/format.ts'
import type { CalendarCell } from './grid.ts'

/** "Provisional (NRT)" for NRT and MIXED months; "Provisional" if only listed in the metadata. */
export function provisionalNote(cell: CalendarCell): string | null {
  if (!cell.provisional) return null
  const level = cell.record?.data_level
  return level !== undefined && level !== 'SP' ? `Provisional (${level})` : 'Provisional'
}

/** One line of text per fact, used by the tooltip, the table and the accessible labels. */
export function cellLines(cell: CalendarCell, source: Source = 'harmonized'): string[] {
  const when = `${MONTH_ABBR[cell.month - 1]} ${cell.year}`
  if (cell.kind === 'outside') return [when, OUTSIDE_RECORD]
  if (cell.kind === 'no-record' || cell.record === null) return [when, NO_RECORD]
  const r = cell.record
  if (source === 'raw') {
    // Raw: only the stored raw count. No verdict, probability, interval or notes.
    const lines = [
      when,
      `Raw combined: ${r.raw_combined_cell_days} fire-active cell-days summed across all operating satellites (not harmonized)`,
    ]
    const note = provisionalNote(cell)
    if (note !== null) lines.push(note)
    return lines
  }
  const verdict = VERDICT_PRESENTATION[r.verdict]
  const probability = verdictProbability(r)
  const lines = [
    when,
    `${verdict.icon} ${verdict.label}${probability === null ? '' : `, ${probability}`}`,
    `Compared with normal: ${formatPctOfNormal(r.pct_of_normal)}`,
    `Harmonized estimate: ${formatEstimate(r)} (${ACTIVITY_UNITS})`,
  ]
  if (r.reason_codes.length > 0) {
    lines.push(`Notes: ${r.reason_codes.map((c) => REASON_CODE_SHORT[c]).join('; ')}`)
  }
  const provisional = provisionalNote(cell)
  if (provisional !== null) lines.push(provisional)
  return lines
}

export function escapeHtml(text: string): string {
  return text
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#39;')
}

/** Tooltip HTML. Every piece of text is escaped. */
export function tooltipHtml(cell: CalendarCell, source: Source = 'harmonized'): string {
  const [title, ...rest] = cellLines(cell, source)
  return `<strong>${escapeHtml(title)}</strong><br/>${rest.map(escapeHtml).join('<br/>')}`
}

/** A single sentence for screen readers. */
export function cellAriaLabel(cell: CalendarCell, source: Source = 'harmonized'): string {
  return cellLines(cell, source).join('. ')
}
