// Texts of the answer panel (T-093): the verdict block, the interval bar, the "Why" chips, the story card, the toasts,
// the loading and error states, and the takeaway under the raw-against-harmonized chart.
// No number is typed here. Every value is passed in from the stored record through the format helpers of
// components/map/format.ts; the two satellite dates come from witnessTimeline.ts. answer.test.ts checks every sentence
// for forbidden claims (fire counts, burned area, cause, forecast, accuracy).
import { monthLabel } from '../state/months.ts'
import type { Witness } from '../api/contract.ts'
import { SATELLITE_TIMELINE } from './witnessTimeline.ts'

/** The quieter unit after the big number (the number itself comes from `formatPctOfNormal`). */
export const PCT_UNIT = '% of normal'

/** The small marker beside the verdict for a near-real-time month (the one provisional notice of the card). */
export const PROVISIONAL_MARK = 'Provisional'

// ---- Interval bar: the estimate and its 90% interval against the normal range ----
export const BAR_ESTIMATE = 'Estimate'
export const BAR_INTERVAL = '90% interval'
export const BAR_NORMAL = 'Normal range'
export const BAR_MEDIAN = 'Median'
/** A stored range, written as the card has always written it: "<low> to <high>". */
export const BAR_RANGE = (low: string, high: string) => `${low} to ${high}`
/** The estimate is there but its interval is not (the wording of `formatEstimate`). */
export const BAR_INTERVAL_MISSING = 'interval not available'
/** A missing normal range or median (the wording of the sparkline for a missing range). */
export const BAR_NOT_AVAILABLE = 'not available'
export const BAR_UNIT_LABEL = 'Unit'
export const BAR_NAME = (area: string) => `${area}: the estimate and its 90% interval against the normal range`
export const BAR_TEXT = (p: { estimate: string; interval: string; normal: string; median: string; unit: string }) =>
  `Estimate ${p.estimate}; 90% interval ${p.interval}; normal range ${p.normal}; median ${p.median}. Unit: ${p.unit}.`
/** Shown instead of the bar when no value of the month can be drawn. */
export const BAR_NONE = 'Nothing to draw for this month: the estimate, its interval and the normal range are all missing.'

// ---- Sparkline caption (the band is defined in the "Normal range" explainer of the interval bar above it) ----
export const SPARK_CAPTION_SHORT = (first: string, last: string, selected: string) =>
  `Estimate by month, ${first} to ${last}; ${selected} marked. Band: normal range.`

// ---- "Why": the stored reason codes as chips ----
export const WHY_HEADING = 'Why'
export const WHY_LABEL = 'Why: the caveats recorded for this month'

// ---- The story card ----
export const STORY_CARD_TITLE = 'Story'

// ---- Toasts ----
export const TOAST_CSV_DOWNLOADED = 'CSV downloaded'
/** How long a toast stays, in milliseconds. */
export const TOAST_MS = 3000

// ---- Actions ----
export const CSV_BUTTON = 'Download CSV'
/** The accessible name keeps the area, and starts with the visible words (WCAG 2.5.3). */
export const CSV_BUTTON_NAME = (area: string) => `Download CSV: ${area}`
export const CSV_PREPARING = 'Preparing CSV…'
export const CSV_ABOUT = 'About the CSV'
export const CSV_FIRMS_LINK = 'Raw hotspot points: NASA FIRMS'
export const ACTIONS_LABEL = 'Actions for this answer'

// ---- Loading and error states ----
export const SUMMARY_LOADING = 'the summary'
export const ANALYTICS_LOADING = 'the analytics'
export const SUMMARY_ERROR = 'Data are not available right now. The summary could not be loaded.'

// ---- The takeaway under the raw-against-harmonized chart (Analytics) ----
const joinMonth = (witness: Witness): string => {
  const entry = SATELLITE_TIMELINE.find((e) => e.witness === witness)
  if (entry === undefined) throw new Error(`No timeline entry for ${witness}`)
  return monthLabel({ year: Number(entry.start.slice(0, 4)), month: Number(entry.start.slice(5, 7)) })
}

/**
 * A description of the method and the sources, true for every area: the raw line sums the detections of every satellite
 * (ANNUAL_NOTE), so a satellite that joins adds its own; the harmonized estimate is in Aqua-equivalent units for every
 * month. Checked on the world series (2011 against 2012, 2017 against 2018) before it was written; it prints no number.
 */
export const RAW_HARMONIZED_TAKEAWAY =
  `Raw adds up the detections of every satellite, so each new one adds its own (S-NPP VIIRS from ${joinMonth('SNPP_VIIRS')}, ` +
  `NOAA-20 VIIRS from ${joinMonth('NOAA20_VIIRS')}); the harmonized estimate keeps every month on the Aqua MODIS scale.`
