import type { MapCell, MapLayer, Metadata } from './contract.ts'
import { parseMapCells, parseMetadata } from './contract.ts'

// Contract v0.1.0 does not define a response envelope or error format (the D-022
// additions are not approved), so these functions expect the bare payload.

export class ApiError extends Error {
  readonly status: number | null
  constructor(message: string, status: number | null) {
    super(message)
    this.name = 'ApiError'
    this.status = status
  }
}

/** Base URL of the API, from VITE_API_BASE_URL (a name only; never a secret). */
export function apiBaseUrl(): string {
  return import.meta.env.VITE_API_BASE_URL ?? ''
}

async function getJson(url: string): Promise<unknown> {
  let response: Response
  try {
    response = await fetch(url)
  } catch {
    throw new ApiError('The data service could not be reached.', null)
  }
  if (!response.ok) {
    throw new ApiError(`The data service returned status ${response.status}.`, response.status)
  }
  return response.json()
}

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
