import type { Anomaly, Bbox, EntityEvidence, EntityItem, EntityMonth, MapCell, MapLayer, Metadata, ValidationResults } from './contract.ts'
import {
  decodeMonth,
  enterStaticMode,
  getStaticBlob,
  getStaticJson,
  monthLabel,
  STATIC_CUSTOM_MESSAGE,
  STATIC_ONLY,
  StaticFileError,
  staticCells,
  staticManifest,
} from './staticData.ts'
import type { EncodedMonth } from './staticData.ts'
import { asCellAreas, asCellColumns, asEncodedMonth, decodeMapCells } from './mapColumns.ts'
import type { CellAreas, CellColumns } from './mapColumns.ts'
import {
  decodeRawByWitness,
  parseAnomalies,
  parseEntityEvidence,
  parseEntityItems,
  parseEntityMonths,
  parseMapCells,
  parseMetadata,
  parseValidationResults,
} from './contract.ts'

// Contract v0.1.0 does not define a response envelope or error format (the D-022
// additions are not approved), so these functions expect the bare payload.

export class ApiError extends Error {
  readonly status: number | null
  /** The server's own message (FastAPI's `detail`), when the response carried one. */
  readonly detail: string | null
  /**
   * True when nothing that speaks for the API answered: the network failed, or the host sent an
   * error that is not the API's own (no JSON `detail`, for example a static host's 404 page or a
   * gateway's 502). Only then may the offline copy stand in (T-043).
   */
  readonly unreachable: boolean
  constructor(message: string, status: number | null, detail: string | null = null, unreachable?: boolean) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.detail = detail
    this.unreachable = unreachable ?? status === null
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
    throw new ApiError(`The data service returned status ${response.status}.`, response.status, detail, detail === null)
  }
  return response.json()
}

const getJson = (url: string) => request(url)

// ---------------------------------------------------------------- the offline copy (T-043)
/** A missing static file is a 404 like the API's; anything else is "not reachable". */
function staticError(error: unknown): ApiError {
  if (error instanceof StaticFileError) {
    return new ApiError(
      error.status === 404 ? 'The data service returned status 404.' : error.message,
      error.status,
    )
  }
  return error instanceof ApiError ? error : new ApiError('The data service could not be reached.', null)
}

/**
 * Answers from the API, or from the offline copy: always from the copy in a static-only build or
 * once the copy is in use; otherwise from the API, and from the copy only when the API cannot be
 * reached and a copy exists. An API error that is an answer (404, 422, 503) is never replaced.
 */
async function route<T>(fromApi: () => Promise<T>, fromStatic: () => Promise<T>): Promise<T> {
  if (STATIC_ONLY || staticManifest() !== null) return fromStatic().catch((e: unknown) => Promise.reject(staticError(e)))
  try {
    return await fromApi()
  } catch (error) {
    if (!(error instanceof ApiError) || !error.unreachable) throw error
    try {
      await enterStaticMode()
    } catch {
      throw error // no offline copy: the original "could not be reached"
    }
    return fromStatic().catch((e: unknown) => Promise.reject(staticError(e)))
  }
}

const staticMeta = async () => {
  await enterStaticMode() // the manifest also switches the app to the offline copy
  return parseMetadata(await getStaticJson('meta.json'))
}

export async function fetchMeta(base: string = apiBaseUrl()): Promise<Metadata> {
  return route(
    async () => parseMetadata(await getJson(`${base}/api/meta`)),
    staticMeta,
  )
}

export async function fetchValidation(base: string = apiBaseUrl()): Promise<ValidationResults> {
  return route(
    async () => parseValidationResults(await getJson(`${base}/api/validation`)),
    async () => parseValidationResults(await getStaticJson('validation.json')),
  )
}

/**
 * The layer asked of GET /api/map/columns. The endpoint sends the same fields for every layer (the
 * fields the map, its tooltip and the evidence panel of a selected cell read), so the app always
 * asks with this one value: a layer change reuses the browser's copy of the month instead of
 * downloading it again.
 */
export const MAP_COLUMNS_LAYER: MapLayer = 'verdict'

/** How long the shared cell list is kept: the grid does not change while the session lasts. */
export const CELL_LIST_TTL_MS = 30 * 60 * 1000

let cellList: { base: string; at: number; promise: Promise<CellColumns> } | null = null
const columnsUnavailable = new Set<string>()

/** Only for tests: forget the cell list and the memory of an API without the columnar endpoints. */
export function resetMapColumns(): void {
  cellList = null
  columnsUnavailable.clear()
}

/** The shared cell list (GET /api/map/cells), fetched once and kept; a failure is not kept. */
function fetchCellList(base: string): Promise<CellColumns> {
  const now = Date.now()
  if (cellList !== null && cellList.base === base && now - cellList.at < CELL_LIST_TTL_MS) return cellList.promise
  const promise = getJson(`${base}/api/map/cells`).then(asCellColumns)
  const entry = { base, at: now, promise }
  cellList = entry
  promise.catch(() => {
    if (cellList === entry) cellList = null
  })
  return promise
}

async function fetchMapCellsFromApi(year: number, month: number, layer: MapLayer, base: string): Promise<MapCell[]> {
  if (!columnsUnavailable.has(base)) {
    const query = new URLSearchParams({ year: String(year), month: String(month), layer: MAP_COLUMNS_LAYER })
    try {
      const [cells, raw] = await Promise.all([fetchCellList(base), getJson(`${base}/api/map/columns?${query.toString()}`)])
      return decodeMapCells(asEncodedMonth(raw), cells)
    } catch (error) {
      // An API without the columnar endpoints answers 404: use /api/map, as before.
      if (!(error instanceof ApiError) || error.status !== 404) throw error
      columnsUnavailable.add(base)
      cellList = null
    }
  }
  const query = new URLSearchParams({ year: String(year), month: String(month), layer })
  return parseMapCells(await getJson(`${base}/api/map?${query.toString()}`))
}

export async function fetchMapCells(
  year: number,
  month: number,
  layer: MapLayer,
  base: string = apiBaseUrl(),
): Promise<MapCell[]> {
  return route(
    () => fetchMapCellsFromApi(year, month, layer, base),
    async () => {
      // The same stored values in the compact layout: every layer has the same fields.
      const [cells, encoded] = await Promise.all([
        staticCells(),
        getStaticJson(`map/${monthLabel(year, month)}.json`),
      ])
      return parseMapCells(decodeMonth(encoded as EncodedMonth, cells))
    },
  )
}

/**
 * The country and continent of every analysis cell (T-090), from the shared cell list that the map already fetches (one request per
 * session). `null` when the API does not send them (an older API, a 404) and in the offline copy, which has no cell list with areas:
 * the caller says so instead of guessing.
 */
export async function fetchCellAreas(base: string = apiBaseUrl()): Promise<CellAreas | null> {
  return route(
    async () => {
      try {
        return asCellAreas(await fetchCellList(base))
      } catch (error) {
        if (error instanceof ApiError && error.status === 404) return null
        throw error
      }
    },
    async () => null,
  )
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
  return route(
    async () => parseEntityMonths(await getJson(`${base}/api/series?${query.toString()}`)),
    async () => parseEntityMonths(await getStaticJson(`series/${entityType}-${entityId}.json`)),
  )
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
  return route(
    async () => parseEntityEvidence(await getJson(`${base}/api/evidence?${query.toString()}`)),
    async () => {
      // One record of the static series, with its stored JSON text decoded as the API does.
      const series = await getStaticJson(`series/${entityType}-${entityId}.json`)
      const record = (Array.isArray(series) ? series : []).find(
        (r: { year?: number; month?: number }) => r.year === year && r.month === month,
      ) as Record<string, unknown> | undefined
      if (record === undefined) throw new StaticFileError('No record for this month.', 404)
      const stored = record.raw_by_witness
      const decoded = typeof stored === 'string' ? (JSON.parse(stored) as unknown) : null
      return parseEntityEvidence({ ...record, raw_by_witness: decodeRawByWitness(decoded, 'evidence') })
    },
  )
}

/** GET /api/entities: the countries or continents present in the products, with their bounds. */
export async function fetchEntities(
  type: 'COUNTRY' | 'CONTINENT',
  base: string = apiBaseUrl(),
): Promise<EntityItem[]> {
  return route(
    async () =>
      parseEntityItems(await getJson(`${base}/api/entities?${new URLSearchParams({ type }).toString()}`)),
    async () => parseEntityItems(await getStaticJson(`entities-${type}.json`)),
  )
}

/**
 * POST /api/series/custom: the monthly series of a custom rectangle, computed by the API
 * through the harmonization function. On a 422 or 503 the server's message is in `ApiError.detail`.
 */
export async function fetchCustomSeries(
  shape: Bbox | { polygon: readonly (readonly number[])[] },
  base: string = apiBaseUrl(),
): Promise<EntityMonth[]> {
  const body = 'polygon' in shape ? { polygon: shape.polygon } : { bbox: shape }
  return route(
    async () =>
      parseEntityMonths(
        await request(`${base}/api/series/custom`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(body),
        }),
      ),
    // The offline copy has the preset views only.
    () => Promise.reject(new ApiError('The offline copy has no custom areas.', 503, STATIC_CUSTOM_MESSAGE)),
  )
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
  return route(
    async () => parseAnomalies(await getJson(`${base}/api/anomalies?${query.toString()}`)),
    async () =>
      parseAnomalies(await getStaticJson(`anomalies/${monthLabel(year, month)}.json`)).slice(0, limit),
  )
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
  | { entity_type: 'CUSTOM'; entity_id: string; bbox: Bbox; polygon?: readonly (readonly number[])[] }

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
  return route(
    () => fetchCsvFromApi(area, synthetic, base),
    async () => {
      if (area.entity_type === 'CUSTOM') {
        throw new ApiError('The offline copy has no custom areas.', 503, STATIC_CUSTOM_MESSAGE)
      }
      // Written by the real export code for every preset area when the copy was made.
      const key = `${area.entity_type}-${area.entity_id}`
      const manifest = await enterStaticMode()
      const filename = manifest.exports[key] ?? fallbackFilename(area, synthetic)
      return { blob: await getStaticBlob(`export/${key}.csv`), filename }
    },
  )
}

async function fetchCsvFromApi(
  area: ExportArea,
  synthetic: boolean,
  base: string,
): Promise<CsvDownload> {
  let response: Response
  try {
    // A polygon of up to 100 points is too long for a URL: POST the same body as the series request.
    response =
      area.entity_type === 'CUSTOM' && area.polygon !== undefined
        ? await fetch(`${base}/api/export.csv`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ polygon: area.polygon }),
          })
        : await fetch(`${base}/api/export.csv?${exportQuery(area)}`)
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
    throw new ApiError(`The data service returned status ${response.status}.`, response.status, detail, detail === null)
  }
  const filename =
    filenameFromDisposition(response.headers.get('Content-Disposition')) ?? fallbackFilename(area, synthetic)
  return { blob: await response.blob(), filename }
}
