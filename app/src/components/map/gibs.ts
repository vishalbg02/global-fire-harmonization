// NASA GIBS imagery under the verdict cells (T-084). Display only: nothing here is a product value.
// Pure helpers (URLs, date limits, opacity, failure rule); the map wiring is in imagery.ts.

const GIBS_BASE = 'https://gibs.earthdata.nasa.gov/wmts/epsg3857/best'

/** Blue Marble shaded relief and bathymetry: a fixed picture of the Earth (the date is the layer's own). */
export const BASEMAP = {
  layer: 'BlueMarble_ShadedRelief_Bathymetry',
  date: '2004-08-01',
  matrixSet: 'GoogleMapsCompatible_Level8',
  extension: 'jpeg',
  /** The last level GIBS serves; MapLibre overzooms it beyond, so no missing tile is requested. */
  maxzoom: 8,
} as const

/** MODIS on Aqua, corrected reflectance (true colour), one image per day. */
export const TRUE_COLOUR = {
  layer: 'MODIS_Aqua_CorrectedReflectance_TrueColor',
  matrixSet: 'GoogleMapsCompatible_Level9',
  extension: 'jpg',
  maxzoom: 9,
  /** First day of Aqua MODIS imagery (2002-07-04). */
  firstDate: '2002-07-04',
} as const

/** The default day of the month for Satellite view. */
export const DEFAULT_SAT_DAY = 15

export const GIBS_LINK = 'https://www.earthdata.nasa.gov/data/tools/gibs'

/** Verdict fill opacity over imagery and on the plain background (Lead's defaults; colour-vision checks in imageryColorVision.test.tsx). */
export const CELL_OPACITY_IMAGERY = 0.78
/** Thin dark casing on each cell over imagery (RGBA): keeps pale verdict fills readable over bright cloud. */
export const CELL_CASING_IMAGERY: readonly [number, number, number, number] = [20, 24, 31, 80]
export const CELL_OPACITY_PLAIN = 0.85

const pad2 = (n: number) => String(n).padStart(2, '0')

export function isoDate(year: number, month: number, day: number): string {
  return `${String(year).padStart(4, '0')}-${pad2(month)}-${pad2(day)}`
}

export function daysInMonth(year: number, month: number): number {
  return new Date(Date.UTC(year, month, 0)).getUTCDate()
}

/** Tile URL template of the Blue Marble basemap (MapLibre fills {z}, {y}, {x}). */
export function basemapTileUrl(): string {
  return `${GIBS_BASE}/${BASEMAP.layer}/default/${BASEMAP.date}/${BASEMAP.matrixSet}/{z}/{y}/{x}.${BASEMAP.extension}`
}

/** Tile URL template of the Aqua true-colour layer for one day (`YYYY-MM-DD`). */
export function trueColourTileUrl(date: string): string {
  return `${GIBS_BASE}/${TRUE_COLOUR.layer}/default/${date}/${TRUE_COLOUR.matrixSet}/{z}/{y}/{x}.${TRUE_COLOUR.extension}`
}

/** Today as `YYYY-MM-DD` in UTC (GIBS dates are UTC days). */
export function todayIso(now: Date = new Date()): string {
  return isoDate(now.getUTCFullYear(), now.getUTCMonth() + 1, now.getUTCDate())
}

/**
 * The days of a month that Satellite view can show: from the first Aqua day, to today at most.
 * Returns null when the whole month is outside that range (before July 2002, or in the future).
 */
export function satDayRange(year: number, month: number, today: string): { first: number; last: number } | null {
  const monthFirst = isoDate(year, month, 1)
  const monthLast = isoDate(year, month, daysInMonth(year, month))
  if (monthLast < TRUE_COLOUR.firstDate || monthFirst > today) return null
  const first = monthFirst < TRUE_COLOUR.firstDate ? Number(TRUE_COLOUR.firstDate.slice(8)) : 1
  const last = monthLast > today ? Number(today.slice(8)) : daysInMonth(year, month)
  return { first, last }
}

/** `day` limited to the days that exist and that GIBS has for the month; null if the month has none. */
export function clampSatDay(year: number, month: number, day: number, today: string): number | null {
  const range = satDayRange(year, month, today)
  if (range === null) return null
  const whole = Number.isFinite(day) ? Math.round(day) : DEFAULT_SAT_DAY
  return Math.min(Math.max(whole, range.first), range.last)
}

/** The satellite date for a month and a wished day, or null when Satellite view is not available for that month. */
export function satDate(year: number, month: number, day: number, today: string): string | null {
  const d = clampSatDay(year, month, day, today)
  return d === null ? null : isoDate(year, month, d)
}

/** Fill opacity of the verdict cells: more see-through over imagery. */
export function cellOpacity(imageryVisible: boolean): number {
  return imageryVisible ? CELL_OPACITY_IMAGERY : CELL_OPACITY_PLAIN
}

/** Tile loading counts of one imagery layer. */
export interface TileStats {
  ok: number
  failed: number
}

/**
 * Whether an imagery layer counts as failed (no network, host blocked, outage): at least three tile
 * errors and more errors than loaded tiles. One missing tile in a day's swath is not a failure.
 */
export function imageryFailed(stats: TileStats): boolean {
  return stats.failed >= 3 && stats.failed > stats.ok
}

export type ImageryNoteKind = 'offline' | 'failed'

/** Which note to show, or null for none: the offline copy never asks GIBS; a failed layer shows one note. */
export function imageryNote(offlineCopy: boolean, basemapFailed: boolean, trueColourFailed: boolean): ImageryNoteKind | null {
  if (offlineCopy) return 'offline'
  return basemapFailed || trueColourFailed ? 'failed' : null
}
