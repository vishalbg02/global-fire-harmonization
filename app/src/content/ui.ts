// Layout strings of the app (T-070): header, toolbar, tabs, map controls, source lines, summary card.
// Member 2 may reword these in T-076 without touching components. Keys are listed in the PR notes.
// Facts (product names, DOIs, method version) are NOT written here: they come from methods.ts and /api/meta.

export const WORDMARK = 'Global Fire Harmonization'
export const TAGLINE = 'Satellite-detected fire activity, harmonized across MODIS and VIIRS'
export const NAV_METHODS = 'Methods and validation'
export const NAV_HOW_TO_READ = 'How to read this'
export const HOW_TO_READ_TITLE = 'How to read this'
export const HOW_TO_READ_INTRO =
  'Each verdict compares the month with what is normal for that calendar month. The five verdicts:'
export const HOW_TO_READ_CLOSE = 'Close'
export const HOW_TO_READ_MORE = 'Read how a verdict is made'

export const TOOLBAR_LABEL = 'Controls'
export const SEARCH_LABEL = 'Area'
export const SEARCH_PLACEHOLDER = 'Search a country or continent'
export const SEARCH_HELP = 'Type to search. Use the arrow keys, Enter to choose, Escape to close.'
export const SEARCH_NO_MATCH = (query: string) => `No country or continent matches "${query}".`
export const SEARCH_RESULTS = (n: number) => `${n} ${n === 1 ? 'area' : 'areas'} found`
export const SEARCH_KIND: Record<'COUNTRY' | 'CONTINENT' | 'GLOBAL', string> = {
  COUNTRY: 'Country',
  CONTINENT: 'Continent',
  GLOBAL: 'World',
}
export const SEARCH_LISTS_FAILED =
  'The country and continent lists could not be loaded. You can still use the world or a custom area.'
export const WORLD_BUTTON = 'World'
export const MONTH_LABEL = 'Month'
export const PLAY = 'Play'
export const PAUSE = 'Pause'
export const PLAY_LABEL = 'Play the months in order'
export const PAUSE_LABEL = 'Pause the time-lapse'
export const REDUCED_MOTION_NOTE =
  'Autoplay is off because your system asks for reduced motion. Use the arrow keys or the buttons to step through the months.'
export const DRAW_MENU = 'Draw or type an area'
export const DRAW_MENU_TITLE = 'Your own area'
export const COPY_LINK = 'Copy link'
export const LINK_COPIED = 'Link copied'
export const LINK_COPY_FAILED = 'The link could not be copied. It is selected below: press Ctrl+C (Command+C on a Mac).'
export const STORIES_LABEL = 'Start with a story:'
export const STORIES_NAV = 'Featured stories'

export const MAP_MODE_LABEL = 'Selection mode'
export const MAP_MODES = { country: 'Country', rectangle: 'Rectangle', polygon: 'Polygon' } as const
export const MAP_MODE_HINT = {
  country: 'Click a country to select it and zoom to it.',
  rectangle: 'Click two opposite corners on the map.',
  polygon: 'Click each corner; double-click or press Enter to finish; Escape drops it.',
} as const
export const HOVER_NO_VERDICT = 'verdict not available for this month'
export const HOVER_LOADING = 'loading the verdict'

export const MAP_SOURCE_LABEL = 'Source'
export const MAP_SOURCE_GRID = '0.5° grid'
export const MAP_SOURCE_STANDARD = 'standard (SP)'
export const MAP_SOURCE_NRT = 'near-real-time (NRT)'
export const MAP_SOURCE_METHOD = (version: string) => `method ${version}`
export const MAP_SOURCE_METHOD_UNKNOWN = 'method version not loaded'

export const TAB_LABELS_UI = {
  calendar: 'Calendar',
  satellites: 'Satellites',
  evidence: 'Evidence in detail',
  anomalies: 'All anomalies',
} as const
export const TABS_LABEL = 'Details for the selected area'

export const SUMMARY_EYEBROW = 'Selected area and month'
export const SUMMARY_NO_MONTH = 'Choose a month to see the summary.'
export const SUMMARY_NO_RECORD = (month: string) => `This area has no record for ${month}.`
export const SUMMARY_SATELLITES = 'Satellites used'
export const SUMMARY_NO_SATELLITES = 'none contributed usable data'
export const SUMMARY_ESTIMATE = 'Estimate'
export const SUMMARY_INTERVAL = '90% interval'
export const SUMMARY_NO_CAVEATS = 'No caveats are recorded for this month.'
export const SUMMARY_LEARN_MORE = 'Learn more'
export const DATA_LEVEL_TEXT: Record<string, string> = {
  SP: 'standard (SP)',
  NRT: 'near-real-time (NRT)',
}
export const SUMMARY_SOURCE_PREFIX = 'Source: NASA FIRMS'
export const SUMMARY_SOURCE_SATELLITES = (names: string) => `satellites used this month: ${names}`
export const SUMMARY_SOURCE_LEVEL = (level: string) => `data level: ${level}`
export const SUMMARY_HOW_MADE = 'How this verdict is made'
export const SUMMARY_METHOD = (version: string) => `method ${version}`

export const SPARK_UNIT = 'fire-active cell-days, Aqua-equivalent'
export const SPARK_CAPTION = (first: string, last: string, selected: string) =>
  `Estimate by month, ${first} to ${last}; ${selected} marked. Band: normal range (25th to 75th percentile).`
export const SPARK_NAME = (area: string) => `Estimate by month for ${area}, with the normal range as a band`
export const SPARK_TEXT = (p: {
  first: string
  last: string
  selected: string
  estimate: string
  range: string
  gaps: number
  months: number
}) =>
  `From ${p.first} to ${p.last}. ${p.selected}: estimate ${p.estimate}; normal range for that month ${p.range}. ` +
  `${p.gaps === 0 ? 'Every month has data.' : `${p.gaps} of ${p.months} months have no data and are left as gaps.`}`
export const SPARK_NO_DATA = 'no data'
export const SPARK_NO_RANGE = 'not available'

export const TOP_ANOMALIES_TITLE = (month: string) => `Biggest anomalies in ${month}`
export const TOP_ANOMALIES_ALL = 'See all anomalies'
export const TOP_ANOMALIES_NONE = 'No areas with a confident above-normal verdict this month.'

export const SELECTION_TITLE = 'Selection'
export const SELECTION_EMPTY = 'Select a cell or a country on the map, or choose an area above.'

export const CAPTION_UNIT = 'Unit'
export const CAPTION_SOURCE = (method: string | null) =>
  `Source: NASA FIRMS, harmonized by this project${method === null ? '' : `, method ${method}`}`
export const CAPTION_UNIT_PCT = '% of normal (the harmonized estimate against the normal range of the same calendar month)'
export const CAPTION_UNIT_HARMONIZED = 'fire-active cell-days, Aqua-equivalent'
export const CAPTION_UNIT_RAW = 'fire-active cell-days, raw (not harmonized)'
export const CAPTION_UNIT_WITNESS =
  'fire-active cell-days: the satellite lines are raw (not harmonized); the harmonized line is Aqua-equivalent'

// Realistic Earth (T-084): imagery under the map, Satellite view, globe, credit and notes.
export const IMAGERY_PANEL = 'Map view'
export const IMAGERY_SATELLITE = 'Satellite view'
export const IMAGERY_SATELLITE_HINT = 'Aqua MODIS true colour for one day of the month'
export const IMAGERY_DAY = 'Day of the month'
export const IMAGERY_SAT_UNAVAILABLE_NO_MONTH = 'Choose a month to use Satellite view.'
export const IMAGERY_SAT_UNAVAILABLE_RANGE = 'Aqua imagery starts on 4 July 2002 and ends today.'
export const IMAGERY_SHAPE = 'Map shape'
export const IMAGERY_FLAT = 'Flat'
export const IMAGERY_GLOBE = 'Globe'
export const IMAGERY_BASEMAP_DATE = 'Blue Marble, shaded relief and bathymetry'
export const IMAGERY_SAT_DATE = (date: string) => `Aqua MODIS true colour, ${date}`
export const IMAGERY_CONTEXT = 'Imagery is context, not data: it has clouds and gaps, and it does not change a verdict.'
export const IMAGERY_CREDIT = 'Imagery: NASA GIBS / EOSDIS'
export const IMAGERY_CREDIT_INFO = 'About the imagery request'
export const IMAGERY_PRIVACY =
  'The imagery is fetched by your browser from NASA GIBS (gibs.earthdata.nasa.gov). NASA GIBS receives the standard tile request, which includes your IP address and the tile coordinates, and nothing else is sent.'
export const IMAGERY_NOTE_FAILED = 'Imagery could not be loaded, so the plain map is shown. The verdict cells are not affected.'
export const IMAGERY_NOTE_OFFLINE = 'Imagery needs an internet connection. This offline copy shows the plain map.'
