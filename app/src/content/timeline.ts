/**
 * Texts of the timeline scrubber (T-093). Plain and factual; no dates or numbers are typed here (the range comes from the
 * metadata and the satellite dates from `witnessTimeline.ts`). The Play, Pause and reduced-motion texts stay in `ui.ts`,
 * the picker's in `monthPicker.ts`.
 */
import { monthLabel } from '../state/months.ts'

export const SLIDER_LABEL = 'Month slider'
export const PREVIOUS_MONTH = 'Previous month'
export const NEXT_MONTH = 'Next month'
export const NO_MONTH = 'No month available'
export const PROVISIONAL = 'Provisional'
export const PROVISIONAL_KEY_LABEL = 'Shaded months are provisional'
export const NO_MAP_SUFFIX = '(no offline map)'
export const SATELLITE_JOINS_LABEL = 'Satellite joins'

/** What the faint line behind the strip shows, for the raw and the harmonized view (also read out with the slider). */
export const LINE_HARMONIZED = 'Faint line: the monthly harmonized estimate of the selected area. Gaps are months without an estimate.'
export const LINE_RAW = 'Faint line: the monthly raw fire-active cell-days of the selected area, satellites not converted. Gaps are months without a record.'
export const LINE_LOADING = 'The line of monthly values appears when the series has loaded.'

/** The value read out by the slider: the month, and whether it is provisional or has no map. */
export function sliderValueText(m: { year: number; month: number } | null, o: { provisional: boolean; noMap: boolean }): string {
  if (m === null) return NO_MONTH
  return `${monthLabel(m)}${o.provisional ? ', provisional' : ''}${o.noMap ? `, ${NO_MAP_SUFFIX.slice(1, -1)}` : ''}`
}

/** The satellite joins, read out with the slider, e.g. "Satellite joins: S-NPP VIIRS in January 2012; ...". */
export function joinsSummary(joins: readonly { label: string; month: { year: number; month: number } }[]): string {
  return joins.length === 0 ? '' : `${SATELLITE_JOINS_LABEL}: ${joins.map((j) => `${j.label} in ${monthLabel(j.month)}`).join('; ')}.`
}
