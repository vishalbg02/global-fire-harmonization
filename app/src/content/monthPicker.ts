/** Texts of the month picker (T-087). Plain and factual; no dates are typed here, the range comes from the metadata. */
export const PICKER_OPEN_LABEL = 'Choose a month'
export const PICKER_TITLE = 'Choose a month'
export const PICKER_YEAR_LABEL = 'Year'
export const PICKER_TYPE_LABEL = 'Type a month (YYYY-MM)'
export const PICKER_TYPE_PLACEHOLDER = 'YYYY-MM'
export const PICKER_GO = 'Go'
export const PICKER_CLOSE = 'Close'
export const PREVIOUS_YEAR_LABEL = 'Previous year'
export const NEXT_YEAR_LABEL = 'Next year'
export const PROVISIONAL_MARK = 'provisional'
export const PICKER_LEGEND = 'A dot marks a provisional month (near-real-time data, may change). Unavailable months are dimmed.'
export const SLIDER_HINT = 'Arrow keys move one month, Page Up and Page Down one year, Home and End the first and last month.'

export const MONTH_ABBREVIATIONS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'] as const

/** The message for text that is not a month of the record; the limits are the first and latest month given. */
export function invalidMonthMessage(first: string, latest: string): string {
  return `Use YYYY-MM, from ${first} to ${latest}.`
}
