import type { ValueMode } from '../state/selection.ts'

export const VALUE_MODE_LABELS: Record<ValueMode, string> = {
  pct: '% of normal',
  activity: 'Activity',
}

export const MONTH_ABBR = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

export const OUTSIDE_RECORD = 'Outside the record'
export const NO_RECORD = 'No data'
export const ACTIVITY_UNITS = 'fire-active cell-days, Aqua-equivalent'
