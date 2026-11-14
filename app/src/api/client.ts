import type { Bbox, EntityEvidence, EntityItem, EntityMonth, MapCell, MapLayer, Metadata } from './contract.ts'
import {
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
