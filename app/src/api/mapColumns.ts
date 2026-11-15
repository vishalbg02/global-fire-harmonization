// The columnar layout of a map month (T-073), shared by GET /api/map/columns and the offline copy
// (api/fire_api/columnar.py writes it, this file reads it). Nothing is computed or rounded: a
// decoded record holds exactly the values that were stored.
//
// A month is one column per field. A column is `{ const }` (the same for every cell), `{ dict, idx }`
// (few distinct values kept once, an index per cell) or `{ values }`. The ids and bounds of the
// cells are in a shared cell list; the month names its cells by position in it (`cell_index`, left
// out when they are its first `n` cells).

import { ContractError, parseMapCellColumns } from './contract.ts'
import type { MapCell } from './contract.ts'

export type CellColumns = Record<string, unknown[]>

export type EncodedColumn = { const: unknown } | { dict: unknown[]; idx: number[] } | { values: unknown[] }

export interface EncodedMonth {
  n: number
  cell_index?: number[]
  columns: Record<string, EncodedColumn>
}

/** The cell list as GET /api/map/cells sends it: `n` cells, one column per field. */
export interface EncodedCells {
  n: number
  columns: CellColumns
}

export const CELL_FIELDS = ['cell_id', 'lat_min', 'lat_max', 'lon_min', 'lon_max'] as const

/** Rebuilds the records of one month from the shared cell list and the month's columns. */
export function decodeMonth(encoded: EncodedMonth, cells: CellColumns): Record<string, unknown>[] {
  const index = encoded.cell_index ?? Array.from({ length: encoded.n }, (_, i) => i)
  const n = index.length
  const ids = cells.cell_id
  const latMin = cells.lat_min
  const latMax = cells.lat_max
  const lonMin = cells.lon_min
  const lonMax = cells.lon_max
  if (ids === undefined || latMin === undefined || latMax === undefined || lonMin === undefined || lonMax === undefined) {
    throw new ContractError('map columns: the cell list is missing a field')
  }
  const out: Record<string, unknown>[] = new Array<Record<string, unknown>>(n)
  for (let i = 0; i < n; i++) {
    const j = index[i] as number
    out[i] = { cell_id: ids[j], lat_min: latMin[j], lat_max: latMax[j], lon_min: lonMin[j], lon_max: lonMax[j] }
  }
  for (const [key, column] of Object.entries(encoded.columns)) {
    if ('const' in column) {
      const value = column.const
      for (let i = 0; i < n; i++) (out[i] as Record<string, unknown>)[key] = value
    } else if ('dict' in column) {
      const { dict, idx } = column
      for (let i = 0; i < n; i++) (out[i] as Record<string, unknown>)[key] = dict[idx[i] as number]
    } else {
      const { values } = column
      for (let i = 0; i < n; i++) (out[i] as Record<string, unknown>)[key] = values[i]
    }
  }
  return out
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value)
}

/** Checks the shape of a response of GET /api/map/columns; the values are checked per cell. */
export function asEncodedMonth(raw: unknown): EncodedMonth {
  if (!isRecord(raw) || typeof raw.n !== 'number' || !isRecord(raw.columns)) {
    throw new ContractError('map columns: expected { n, columns }')
  }
  const length = raw.cell_index === undefined ? raw.n : Array.isArray(raw.cell_index) ? raw.cell_index.length : -1
  if (length !== raw.n) throw new ContractError('map columns: cell_index does not match n')
  for (const [key, column] of Object.entries(raw.columns)) {
    const ok =
      isRecord(column) &&
      ('const' in column ||
        (Array.isArray(column.dict) && Array.isArray(column.idx) && column.idx.length === raw.n) ||
        (Array.isArray(column.values) && column.values.length === raw.n))
    if (!ok) throw new ContractError(`map columns: column "${key}" is malformed`)
  }
  return raw as unknown as EncodedMonth
}

/** Checks the shape of a response of GET /api/map/cells. */
export function asCellColumns(raw: unknown): CellColumns {
  if (!isRecord(raw) || typeof raw.n !== 'number' || !isRecord(raw.columns)) {
    throw new ContractError('map cells: expected { n, columns }')
  }
  for (const key of CELL_FIELDS) {
    const column = raw.columns[key]
    if (!Array.isArray(column) || column.length !== raw.n) throw new ContractError(`map cells: column "${key}" is malformed`)
  }
  return raw.columns as CellColumns
}

/**
 * The map cells of one month from GET /api/map/columns and the shared cell list: decoded, then
 * each record checked as `parseMapCellColumns` does. The result is the same cell objects the map
 * has always used (the fields the map never reads are absent, not invented).
 */
export function decodeMapCells(encoded: EncodedMonth, cells: CellColumns): MapCell[] {
  const records = decodeMonth(encoded, cells)
  const size = (cells.cell_id as unknown[]).length
  for (const j of encoded.cell_index ?? []) {
    if (!Number.isInteger(j) || j < 0 || j >= size) throw new ContractError('map columns: cell_index is out of range')
  }
  if (encoded.cell_index === undefined && encoded.n > size) throw new ContractError('map columns: more cells than the cell list')
  return records.map(parseMapCellColumns)
}

/**
 * The country and the continent of every cell, as GET /api/map/cells sends them since T-090 (stored in cells.parquet; `null` for a cell
 * with none). An API that does not send the two columns (an older one) gives `null` here, never an invented value.
 */
export interface CellAreas {
  cell_id: readonly string[]
  country_iso3: readonly (string | null)[]
  continent: readonly (string | null)[]
}

export function asCellAreas(columns: CellColumns): CellAreas | null {
  const ids = columns.cell_id
  const country = columns.country_iso3
  const continent = columns.continent
  if (country === undefined || continent === undefined) return null
  const text = (column: unknown[]) => column.every((v) => v === null || typeof v === 'string')
  if (country.length !== ids.length || continent.length !== ids.length || !text(country) || !text(continent)) {
    throw new ContractError('map cells: the country and continent columns are malformed')
  }
  return { cell_id: ids as string[], country_iso3: country as (string | null)[], continent: continent as (string | null)[] }
}
