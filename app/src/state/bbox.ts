import type { Bbox } from '../api/contract.ts'
import type { CustomArea } from './selection.ts'

export type BboxCheck = { ok: true; bbox: Bbox } | { ok: false; message: string }

export interface BboxFields {
  west: string
  south: string
  east: string
  north: string
}

const LIMITS = { west: 180, east: 180, south: 90, north: 90 } as const

const round2 = (v: number) => (Math.round(v * 100) / 100).toFixed(2)

/**
 * Checks a box before it is sent. These checks only stop obviously invalid boxes with a clear
 * message; the API validates again, and which grid cells fall inside is decided by the API.
 */
export function checkBbox(west: number, south: number, east: number, north: number): BboxCheck {
  const values = { west, south, east, north }
  for (const key of ['west', 'south', 'east', 'north'] as const) {
    const v = values[key]
    if (!Number.isFinite(v)) return { ok: false, message: `Enter a number for ${key}.` }
    if (Math.abs(v) > LIMITS[key]) {
      return { ok: false, message: `${key[0].toUpperCase()}${key.slice(1)} must be between -${LIMITS[key]} and ${LIMITS[key]}.` }
    }
  }
  if (west > east) {
    return {
      ok: false,
      message:
        'West must be less than east. Boxes that cross the antimeridian (180 degrees) are not supported.',
    }
  }
  if (west === east) return { ok: false, message: 'West must be less than east.' }
  if (south >= north) return { ok: false, message: 'South must be less than north.' }
  return { ok: true, bbox: [west, south, east, north] }
}

/** Parses the four text fields of the form. An empty field is "Enter a number". */
export function parseBboxFields(fields: BboxFields): BboxCheck {
  const toNumber = (text: string) => (text.trim() === '' ? Number.NaN : Number(text))
  return checkBbox(toNumber(fields.west), toNumber(fields.south), toNumber(fields.east), toNumber(fields.north))
}

/** "custom_w{W}_s{S}_e{E}_n{N}", bounds rounded to 2 decimals (the proposed contract id). */
export function customId(bbox: Bbox): string {
  const [w, s, e, n] = bbox
  return `custom_w${round2(w)}_s${round2(s)}_e${round2(e)}_n${round2(n)}`
}

export function customArea(bbox: Bbox): CustomArea {
  return { entity_type: 'CUSTOM', entity_id: customId(bbox), entity_name: 'Custom area', bbox }
}

/** "W 100.00, S 0.00, E 101.00, N 1.00" */
export function bboxLabel(bbox: Bbox): string {
  const [w, s, e, n] = bbox
  return `W ${round2(w)}, S ${round2(s)}, E ${round2(e)}, N ${round2(n)}`
}

/**
 * The box around a drawn rectangle (a ring of [longitude, latitude] points): the smallest box
 * containing the points, clamped to valid degrees and rounded to 2 decimals, then checked like
 * a typed box. A rectangle too small to survive the rounding is rejected by the check.
 */
export function bboxFromRing(ring: readonly (readonly number[])[]): BboxCheck {
  if (ring.length === 0) return { ok: false, message: 'The drawn rectangle has no points.' }
  const lons = ring.map((p) => p[0])
  const lats = ring.map((p) => p[1])
  const tidy = (v: number, limit: number) => Math.round(Math.max(-limit, Math.min(limit, v)) * 100) / 100
  return checkBbox(
    tidy(Math.min(...lons), 180),
    tidy(Math.min(...lats), 90),
    tidy(Math.max(...lons), 180),
    tidy(Math.max(...lats), 90),
  )
}
