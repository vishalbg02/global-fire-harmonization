// The offline copy of the preset views (T-043): static JSON files written by
// api/fire_api/static_export.py. Every file is the API's own answer; nothing is computed here.

import { useSyncExternalStore } from 'react'

/** Message shown wherever a custom area or a drawn box is asked for in the offline copy. */
export const STATIC_CUSTOM_MESSAGE =
  'Custom areas need the live service. This offline copy has the preset views only.'

export interface StaticManifest {
  format_version: number
  exported_at: string
  synthetic: boolean
  contract_version: string
  method_version: string
  data_snapshot: { zips_downloaded?: string | null; api_pulled?: string | null } | null
  months: string[]
  exports: Record<string, string>
}

/** `VITE_STATIC_ONLY=1` builds the app for a deployment with no API at all. */
export const STATIC_ONLY = import.meta.env.VITE_STATIC_ONLY === '1'

/** Where the files are served from: `data/` next to the page (`app/public/data`). */
export function staticBase(): string {
  return `${import.meta.env.BASE_URL}data`
}

// ------------------------------------------------------------------ the shared mode state
let manifest: StaticManifest | null = null
const listeners = new Set<() => void>()

function setManifest(value: StaticManifest): void {
  manifest = value
  listeners.forEach((l) => l())
}

/** The manifest while the app shows the offline copy, else null. */
export function staticManifest(): StaticManifest | null {
  return manifest
}

export function useStaticManifest(): StaticManifest | null {
  return useSyncExternalStore(
    (onChange) => {
      listeners.add(onChange)
      return () => listeners.delete(onChange)
    },
    () => manifest,
    () => manifest, // client-only app: no separate server snapshot
  )
}

/** Only for tests. */
export function resetStaticMode(): void {
  manifest = null
  loading = null
  cellsPromise = null
  listeners.forEach((l) => l())
}

// ------------------------------------------------------------------ reading the files
export class StaticFileError extends Error {
  readonly status: number | null
  constructor(message: string, status: number | null) {
    super(message)
    this.name = 'StaticFileError'
    this.status = status
  }
}

/** One JSON file of the copy. A missing file (or a server that answers with the page) is a 404. */
export async function getStaticJson(path: string): Promise<unknown> {
  let response: Response
  try {
    response = await fetch(`${staticBase()}/${path}`)
  } catch {
    throw new StaticFileError('The offline copy could not be reached.', null)
  }
  if (!response.ok) throw new StaticFileError(`The offline copy has no ${path}.`, response.status)
  try {
    return await response.json()
  } catch {
    // A static host that serves the page for unknown paths answers with HTML.
    throw new StaticFileError(`The offline copy has no ${path}.`, 404)
  }
}

export async function getStaticBlob(path: string): Promise<Blob> {
  let response: Response
  try {
    response = await fetch(`${staticBase()}/${path}`)
  } catch {
    throw new StaticFileError('The offline copy could not be reached.', null)
  }
  if (!response.ok) throw new StaticFileError(`The offline copy has no ${path}.`, response.status)
  return response.blob()
}

function parseManifest(raw: unknown): StaticManifest {
  if (typeof raw !== 'object' || raw === null) throw new StaticFileError('The offline copy has no manifest.', 404)
  const o = raw as Record<string, unknown>
  if (o.format_version !== 1 || typeof o.exported_at !== 'string' || !Array.isArray(o.months)) {
    throw new StaticFileError('The offline copy has an unknown format.', 404)
  }
  return o as unknown as StaticManifest
}

let loading: Promise<StaticManifest> | null = null

/** Loads the manifest once and switches the app to the offline copy. Rejects when there is no copy. */
export function enterStaticMode(): Promise<StaticManifest> {
  if (manifest !== null) return Promise.resolve(manifest)
  loading ??= getStaticJson('manifest.json')
    .then(parseManifest)
    .then((m) => {
      setManifest(m)
      return m
    })
    .catch((error: unknown) => {
      loading = null
      throw error
    })
  return loading
}

// ------------------------------------------------------------------ the compact map layout
export type CellColumns = Record<string, unknown[]>

export interface EncodedMonth {
  n: number
  cell_index?: number[]
  columns: Record<string, { const: unknown } | { dict: unknown[]; idx: number[] } | { values: unknown[] }>
}

const CELL_FIELDS = ['cell_id', 'lat_min', 'lat_max', 'lon_min', 'lon_max'] as const

/** Rebuilds the API's records of one month from the shared cell list and the month's columns. */
export function decodeMonth(encoded: EncodedMonth, cells: CellColumns): Record<string, unknown>[] {
  const index = encoded.cell_index ?? Array.from({ length: encoded.n }, (_, i) => i)
  const out: Record<string, unknown>[] = index.map((j) => {
    const record: Record<string, unknown> = {}
    for (const key of CELL_FIELDS) record[key] = (cells[key] as unknown[])[j]
    return record
  })
  for (const [key, column] of Object.entries(encoded.columns)) {
    out.forEach((record, i) => {
      if ('const' in column) record[key] = column.const
      else if ('dict' in column) record[key] = column.dict[column.idx[i] as number]
      else record[key] = column.values[i]
    })
  }
  return out
}

let cellsPromise: Promise<CellColumns> | null = null

/** The shared cell list (ids and bounds), loaded once. */
export function staticCells(): Promise<CellColumns> {
  cellsPromise ??= getStaticJson('cells.json')
    .then((raw) => raw as CellColumns)
    .catch((error: unknown) => {
      cellsPromise = null
      throw error
    })
  return cellsPromise
}

export function monthLabel(year: number, month: number): string {
  return `${year}-${String(month).padStart(2, '0')}`
}
