import type { Anomaly, Bbox, EntityEvidence, EntityItem, EntityMonth, MapCell, MapLayer, Metadata } from './contract.ts'
import {
  parseAnomalies,
  parseEntityEvidence,
  parseEntityItems,
  parseEntityMonths,
  parseMapCells,
  parseMetadata,
} from './contract.ts'

// Contract v0.1.0 does not define a response envelope or error format (the D-022
// additions are not approved), so these functions expect the bare payload.

export class ApiError extends Error {
  readonly status: number | null
  /** The server's own message (FastAPI's `detail`), when the response carried one. */
  readonly detail: string | null
  constructor(message: string, status: number | null, detail: string | null = null) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.detail = detail
  }
}

/** FastAPI's default error body is `{"detail": "text"}` or `{"detail": [{"msg": "text", ...}]}`. */
export function errorDetail(body: unknown): string | null {
  if (typeof body !== 'object' || body === null || !('detail' in body)) return null
  const detail = (body as { detail: unknown }).detail
  if (typeof detail === 'string' && detail.trim() !== '') return detail
  if (Array.isArray(detail)) {
    const messages = detail
      .map((d) => (typeof d === 'object' && d !== null && 'msg' in d ? String((d as { msg: unknown }).msg) : ''))
      .filter((m) => m !== '')
    return messages.length > 0 ? messages.join('; ') : null
  }
  return null
}

/** Base URL of the API, from VITE_API_BASE_URL (a name only; never a secret). */
export function apiBaseUrl(): string {
  return import.meta.env.VITE_API_BASE_URL ?? ''
}

async function request(url: string, init?: RequestInit): Promise<unknown> {
  let response: Response
  try {
    response = init === undefined ? await fetch(url) : await fetch(url, init)
  } catch {
    throw new ApiError('The data service could not be reached.', null)
  }
  if (!response.ok) {
    let detail: string | null = null
    try {
      detail = errorDetail(await response.json())
    } catch {
      detail = null
    }
    throw new ApiError(`The data service returned status ${response.status}.`, response.status, detail)
  }
  return response.json()
}

const getJson = (url: string) => request(url)

export async function fetchMeta(base: string = apiBaseUrl()): Promise<Metadata> {
  return parseMetadata(await getJson(`${base}/api/meta`))
}

export async function fetchMapCells(
  year: number,
  month: number,
  layer: MapLayer,
  base: string = apiBaseUrl(),
): Promise<MapCell[]> {
  const query = new URLSearchParams({ year: String(year), month: String(month), layer })
  return parseMapCells(await getJson(`${base}/api/map?${query.toString()}`))
}

/** Entity types the series endpoint serves (the ones stored in entity_month). */
export type SeriesEntityType = 'COUNTRY' | 'CONTINENT' | 'GLOBAL'

/** GET /api/series: the monthly records of a preset entity. A 404 means the entity is unknown. */
export async function fetchSeries(
  entityType: SeriesEntityType,
  entityId: string,
  base: string = apiBaseUrl(),
): Promise<EntityMonth[]> {
  const query = new URLSearchParams({ entity_type: entityType, entity_id: entityId })
  return parseEntityMonths(await getJson(`${base}/api/series?${query.toString()}`))
}

/** GET /api/evidence: one entity_month record for a month. A 404 means the entity or month is unknown. */
export async function fetchEvidence(
  entityType: SeriesEntityType,
  entityId: string,
  year: number,
  month: number,
  base: string = apiBaseUrl(),
): Promise<EntityEvidence> {
  const query = new URLSearchParams({
    entity_type: entityType,
    entity_id: entityId,
    year: String(year),
    month: String(month),
  })
  return parseEntityEvidence(await getJson(`${base}/api/evidence?${query.toString()}`))
}

/** GET /api/entities: the countries or continents present in the products, with their bounds. */
export async function fetchEntities(
  type: 'COUNTRY' | 'CONTINENT',
  base: string = apiBaseUrl(),
): Promise<EntityItem[]> {
  return parseEntityItems(await getJson(`${base}/api/entities?${new URLSearchParams({ type }).toString()}`))
}

/**
 * POST /api/series/custom: the monthly series of a custom rectangle, computed by the API
 * through the harmonization function. On a 422 or 503 the server's message is in `ApiError.detail`.
 */
export async function fetchCustomSeries(bbox: Bbox, base: string = apiBaseUrl()): Promise<EntityMonth[]> {
  const body = await request(`${base}/api/series/custom`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ bbox }),
  })
  return parseEntityMonths(body)
}

/** The most anomalies the API returns in one call (its documented maximum). */
export const ANOMALIES_MAX_LIMIT = 500

/**
 * GET /api/anomalies: the areas with an above- or below-normal verdict in a month, in the API's
 * order. The app asks for the maximum so that it can rank per verdict and per type itself.
 */
export async function fetchAnomalies(
  year: number,
  month: number,
  limit: number = ANOMALIES_MAX_LIMIT,
  base: string = apiBaseUrl(),
): Promise<Anomaly[]> {
  const query = new URLSearchParams({ year: String(year), month: String(month), limit: String(limit) })
  return parseAnomalies(await getJson(`${base}/api/anomalies?${query.toString()}`))
}

/** The query string of `GET /api/export.csv` for a preset area or a custom rectangle (W,S,E,N). */
export function exportQuery(area: ExportArea): string {
  if (area.entity_type === 'CUSTOM') {
    return new URLSearchParams({ bbox: area.bbox.join(',') }).toString()
  }
  return new URLSearchParams({ entity_type: area.entity_type, entity_id: area.entity_id }).toString()
}

/** The area an export is made for: a preset entity or a custom rectangle. */
export type ExportArea =
  | { entity_type: SeriesEntityType; entity_id: string }
  | { entity_type: 'CUSTOM'; entity_id: string; bbox: Bbox }

/** The file name the server sent in `Content-Disposition`, or null when it sent none. */
export function filenameFromDisposition(header: string | null): string | null {
  if (header === null) return null
  const quoted = /filename="([^"]+)"/i.exec(header)
  const bare = /filename=([^;\s]+)/i.exec(header)
  const name = (quoted?.[1] ?? bare?.[1] ?? '').trim()
  return name === '' ? null : name
}

/** Used only when the server sends no file name. Marked SYNTHETIC while the data are. */
export function fallbackFilename(area: ExportArea, synthetic: boolean): string {
  const safe = (t: string) => t.replace(/[^A-Za-z0-9._-]+/g, '-')
  return `${synthetic ? 'SYNTHETIC_' : ''}fire-harmonization_${safe(area.entity_type)}_${safe(area.entity_id)}.csv`
}

export interface CsvDownload {
  blob: Blob
  filename: string
}

/** GET /api/export.csv. Errors carry the server's message (for example the custom-area 503). */
export async function fetchCsv(
  area: ExportArea,
  synthetic: boolean,
  base: string = apiBaseUrl(),
): Promise<CsvDownload> {
  let response: Response
  try {
    response = await fetch(`${base}/api/export.csv?${exportQuery(area)}`)
  } catch {
    throw new ApiError('The data service could not be reached.', null)
  }
  if (!response.ok) {
    let detail: string | null = null
    try {
      detail = errorDetail(await response.json())
    } catch {
      detail = null
    }
    throw new ApiError(`The data service returned status ${response.status}.`, response.status, detail)
  }
  const filename =
    filenameFromDisposition(response.headers.get('Content-Disposition')) ?? fallbackFilename(area, synthetic)
  return { blob: await response.blob(), filename }
}
