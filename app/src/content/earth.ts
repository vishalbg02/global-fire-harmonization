// Sentences of the Earth view (T-093 phase 2): the legend's "Show all verdicts" switch and its one-line rule, and the
// rotation control. Display only; no number is stated here. Tested in earth.test.ts.

/** The legend switch that draws every verdict at full strength at every zoom (link `allv=1`). */
export const SHOW_ALL_VERDICTS = 'Show all verdicts'
/** The one quiet line under the verdict legend while the low-zoom rule is in effect. */
export const SIGNAL_RULE = 'Zoomed out, only above and below normal are drawn strongly.'
/** The name of the screen-reader list of colours shown when the legend is folded. */
export const LEGEND_COLOURS = 'Verdict colours'
/** The button beside the zoom buttons that stops and restarts the slow turning of the globe (`aria-pressed`). */
export const PAUSE_ROTATION = 'Pause rotation'
/** Its tooltip while the globe may turn, and while it is paused. */
export const PAUSE_ROTATION_TITLE = 'Pause the slow turning of the globe'
export const RESUME_ROTATION_TITLE = 'Resume the slow turning of the globe'

/** Every sentence above, for the wording test. */
export const EARTH_TEXTS: readonly string[] = [
  SHOW_ALL_VERDICTS,
  SIGNAL_RULE,
  LEGEND_COLOURS,
  PAUSE_ROTATION,
  PAUSE_ROTATION_TITLE,
  RESUME_ROTATION_TITLE,
]
