import type { Bbox } from '../api/contract.ts'
import type { CustomArea } from './selection.ts'

/** One outer ring of [longitude, latitude] points, the first point not repeated at the end. */
export type Ring = [number, number][]

export type PolygonCheck = { ok: true; ring: Ring } | { ok: false; message: string }

/** At most this many corner points (the API's limit). */
export const MAX_POLYGON_POINTS = 100

// The messages are the API's, word for word, so a client-side check and a 422 read the same.
export const POLYGON_MESSAGES = {
  notEnough: 'A polygon needs at least 3 different corner points.',
  tooMany: `A polygon can have at most ${MAX_POLYGON_POINTS} corner points.`,
  notFinite: 'Every corner point must be a pair of finite numbers: longitude, latitude.',
  outOfRange: 'Every corner point must have -180 <= longitude <= 180 and -90 <= latitude <= 90.',
  repeated:
    'Corner points must all be different: do not repeat the first point at the end (the polygon is closed automatically).',
  antimeridian:
    'Polygons that cross the antimeridian (longitude 180) are not supported: no side may span more than 180 degrees of longitude.',
  noArea:
    'The polygon has no area: its corner points lie on one line, or its bounding box needs west < east and south < north.',
  selfIntersecting:
    'The polygon crosses or touches itself (or two of its sides overlap). Use a simple outline whose sides only meet at their corners.',
} as const

type P = readonly [number, number]

const round4 = (v: number) => Math.round(v * 10000) / 10000

/** Sign of (b - a) x (p - a). Coordinates have at most 4 decimals, so float noise is far below 1e-9. */
function orient(a: P, b: P, p: P): number {
  const cross = (b[0] - a[0]) * (p[1] - a[1]) - (b[1] - a[1]) * (p[0] - a[0])
  return Math.abs(cross) < 1e-9 ? 0 : Math.sign(cross)
}

const inBox = (a: P, b: P, p: P) =>
  Math.min(a[0], b[0]) <= p[0] && p[0] <= Math.max(a[0], b[0]) && Math.min(a[1], b[1]) <= p[1] && p[1] <= Math.max(a[1], b[1])

function segmentsMeet(a: P, b: P, c: P, d: P): boolean {
  const o1 = orient(a, b, c)
  const o2 = orient(a, b, d)
  const o3 = orient(c, d, a)
  const o4 = orient(c, d, b)
  if (o1 !== o2 && o3 !== o4) return true
  return (o1 === 0 && inBox(a, b, c)) || (o2 === 0 && inBox(a, b, d)) || (o3 === 0 && inBox(c, d, a)) || (o4 === 0 && inBox(c, d, b))
}

function foldsBack(a: P, b: P, c: P): boolean {
  if (orient(a, b, c) !== 0) return false
  return (a[0] - b[0]) * (c[0] - b[0]) + (a[1] - b[1]) * (c[1] - b[1]) > 0
}

/**
 * Checks a ring before it is sent, with the API's rules and messages: 3 to 100 different finite
 * points inside the world box, the first point not repeated, no side spanning more than 180
 * degrees of longitude, a non-zero area and no self-intersection. The API validates again.
 */
export function checkRing(points: readonly (readonly number[])[]): PolygonCheck {
  if (points.length > MAX_POLYGON_POINTS) {
    return { ok: false, message: `${POLYGON_MESSAGES.tooMany} This one has ${points.length}.` }
  }
  if (points.some((p) => p.length !== 2 || !Number.isFinite(p[0]) || !Number.isFinite(p[1]))) {
    return { ok: false, message: POLYGON_MESSAGES.notFinite }
  }
  const ring: Ring = points.map((p) => [p[0], p[1]])
  if (ring.some(([lon, lat]) => Math.abs(lon) > 180 || Math.abs(lat) > 90)) {
    return { ok: false, message: POLYGON_MESSAGES.outOfRange }
  }
  const distinct = new Set(ring.map((p) => `${p[0]},${p[1]}`)).size
  if (distinct < 3) return { ok: false, message: POLYGON_MESSAGES.notEnough }
  if (distinct !== ring.length) return { ok: false, message: POLYGON_MESSAGES.repeated }
  const n = ring.length
  const sides = ring.map((p, i) => [p, ring[(i + 1) % n]] as const)
  if (sides.some(([a, b]) => Math.abs(a[0] - b[0]) > 180)) return { ok: false, message: POLYGON_MESSAGES.antimeridian }
  const [west, south, east, north] = ringBounds(ring)
  if (!(west < east && south < north) || ring.slice(2).every((p) => orient(ring[0], ring[1], p) === 0)) {
    return { ok: false, message: POLYGON_MESSAGES.noArea }
  }
  for (let i = 0; i < n; i++) {
    if (foldsBack(ring[(i + n - 1) % n], ring[i], ring[(i + 1) % n])) {
      return { ok: false, message: POLYGON_MESSAGES.selfIntersecting }
    }
    for (let j = i + 2; j < n; j++) {
      if (i === 0 && j === n - 1) continue // the closing side is adjacent to the first
      if (segmentsMeet(...sides[i], ...sides[j])) return { ok: false, message: POLYGON_MESSAGES.selfIntersecting }
    }
  }
  return { ok: true, ring }
}

/** Rounds to the 4 decimals the link keeps (about 11 m), then checks the rounded ring. */
export function checkRoundedRing(points: readonly (readonly number[])[]): PolygonCheck {
  return checkRing(points.map((p) => (p.length === 2 ? [round4(p[0]), round4(p[1])] : p)))
}

/**
 * The ring typed in the text box: one `longitude, latitude` per line, separated by a comma and/or
 * spaces; blank lines are ignored. Then the same checks as the API.
 */
export function parsePolygonText(text: string): PolygonCheck {
  const points: number[][] = []
  const lines = text.split(/\r?\n/)
  for (let i = 0; i < lines.length; i++) {
    const line = lines[i].trim()
    if (line === '') continue
    const parts = line.split(/[\s,]+/).filter((p) => p !== '')
    const numbers = parts.map((p) => (/^[-+]?(\d+\.?\d*|\.\d+)([eE][-+]?\d+)?$/.test(p) ? Number(p) : Number.NaN))
    if (parts.length !== 2 || numbers.some((v) => !Number.isFinite(v))) {
      return { ok: false, message: `Line ${i + 1}: enter a longitude and a latitude, two numbers such as "100.25, 0.5".` }
    }
    points.push(numbers)
  }
  if (points.length === 0) return { ok: false, message: 'Enter the corner points, one "longitude, latitude" per line.' }
  return checkRoundedRing(points)
}

/** A drawn ring (terra-draw closes it by repeating the first point) as the open ring we keep. */
export function openRing(ring: readonly (readonly number[])[]): number[][] {
  const last = ring.length - 1
  if (last >= 1 && ring[0][0] === ring[last][0] && ring[0][1] === ring[last][1]) return ring.slice(0, last).map((p) => [...p])
  return ring.map((p) => [...p])
}

export function ringBounds(ring: readonly P[]): Bbox {
  const lons = ring.map((p) => p[0])
  const lats = ring.map((p) => p[1])
  return [Math.min(...lons), Math.min(...lats), Math.max(...lons), Math.max(...lats)]
}

/** "lon,lat;lon,lat;..." (the link format, after `POLY:`). */
export function ringToLinkText(ring: readonly P[]): string {
  return ring.map(([lon, lat]) => `${round4(lon)},${round4(lat)}`).join(';')
}

/** One "longitude, latitude" per line, for the text box. */
export function ringToLines(ring: readonly P[]): string {
  return ring.map(([lon, lat]) => `${round4(lon)}, ${round4(lat)}`).join('\n')
}

/**
 * The ring of a link. Anything malformed, over the limit or not a valid polygon gives null (a
 * link is never an error).
 */
export function ringFromLinkText(text: string): Ring | null {
  if (text === '' || text.length > 4000) return null
  const points = text.split(';').map((pair) => pair.split(','))
  if (points.length > MAX_POLYGON_POINTS) return null
  const numbers: number[][] = []
  for (const parts of points) {
    if (parts.length !== 2 || parts.some((p) => p.trim() === '')) return null
    numbers.push(parts.map(Number))
  }
  const check = checkRoundedRing(numbers)
  return check.ok ? check.ring : null
}

/** A short stable id of the ring (FNV-1a of its link text), so two polygons never share one. */
function ringHash(ring: readonly P[]): string {
  let h = 0x811c9dc5
  for (const ch of ringToLinkText(ring)) {
    h ^= ch.codePointAt(0) ?? 0
    h = Math.imul(h, 0x01000193) >>> 0
  }
  return h.toString(16).padStart(8, '0')
}

export function polygonId(ring: readonly P[]): string {
  return `custom_poly${ring.length}_${ringHash(ring)}`
}

/** A custom area drawn or typed as a polygon; `bbox` is the ring's bounding box. */
export function polygonArea(ring: Ring): CustomArea {
  return {
    entity_type: 'CUSTOM',
    entity_id: polygonId(ring),
    entity_name: 'Custom polygon',
    bbox: ringBounds(ring),
    polygon: ring,
  }
}

/** The announcement of a polygon area; the cell count is added once the series is known. */
export function polygonAnnouncement(points: number, cells: number | null): string {
  const base = `Custom polygon, ${points} corner points`
  return cells === null ? base : `${base}, ${cells} grid cells`
}

/** What decides which cells belong to a polygon, shown next to it. */
export const POLYGON_NOTE =
  'A grid cell belongs to the polygon when its centre lies inside it (the edge included). A cell the polygon covers 60% but whose centre is outside is left out, and a very small polygon may contain no cell centre at all. Up to 100 corner points; outlines that cross themselves or the antimeridian (180 degrees) are not supported. Coordinates are kept to 4 decimals.'

export const POLYGON_DRAW_HINT =
  'Click each corner on the map. Finish with a double-click or the Enter key; Escape drops the polygon being drawn. Drawing needs a pointer; use the text box above to enter the corner points with the keyboard.'
