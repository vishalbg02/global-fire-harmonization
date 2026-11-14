import type { Bbox } from '../api/contract.ts'
import { checkBbox, customArea } from './bbox.ts'
import { initialSelection, WORLD } from './selection.ts'
import type { Area, MapMode, Selection, Source, ValueMode } from './selection.ts'

/** The part of the selection that a shared link carries. */
export type LinkedSelection = Pick<Selection, 'area' | 'month' | 'source' | 'mapMode' | 'valueMode'>

const COUNTRY_ID = /^[A-Z0-9]{2,3}$/
const CONTINENT_ID = /^[A-Z]{2}$/
const MONTH = /^(\d{4})-(0[1-9]|1[0-2])$/

function areaToText(area: Area): string {
  if (area.entity_type === 'GLOBAL') return 'GLOBAL'
  if (area.entity_type === 'CUSTOM') return `CUSTOM:${area.bbox.join(',')}`
  return `${area.entity_type}:${area.entity_id}`
}

/** The query string (without "?") for a selection. Defaults are left out to keep links short. */
export function encodeSelection(sel: LinkedSelection): string {
  const params = new URLSearchParams()
  if (sel.area.entity_type !== 'GLOBAL') params.set('area', areaToText(sel.area))
  if (sel.month !== null) params.set('month', `${sel.month.year}-${String(sel.month.month).padStart(2, '0')}`)
  if (sel.source !== initialSelection.source) params.set('source', sel.source)
  if (sel.mapMode !== initialSelection.mapMode) params.set('map', sel.mapMode)
  if (sel.valueMode !== initialSelection.valueMode) params.set('value', sel.valueMode)
  return params.toString()
}

function areaFromText(text: string | null): Area | null {
  if (text === null) return null
  if (text === 'GLOBAL') return WORLD
  const [kind, rest = ''] = [text.slice(0, text.indexOf(':')), text.slice(text.indexOf(':') + 1)]
  if (kind === 'COUNTRY' && COUNTRY_ID.test(rest)) {
    return { entity_type: 'COUNTRY', entity_id: rest, entity_name: rest }
  }
  if (kind === 'CONTINENT' && CONTINENT_ID.test(rest)) {
    return { entity_type: 'CONTINENT', entity_id: rest, entity_name: rest }
  }
  if (kind === 'CUSTOM') {
    const parts = rest.split(',')
    if (parts.length !== 4) return null
    const [w, s, e, n] = parts.map((p) => (p.trim() === '' ? Number.NaN : Number(p)))
    const check = checkBbox(w, s, e, n)
    return check.ok ? customArea(check.bbox as Bbox) : null
  }
  return null
}

function oneOf<T extends string>(value: string | null, allowed: readonly T[]): T | null {
  return value !== null && (allowed as readonly string[]).includes(value) ? (value as T) : null
}

/**
 * The selection a link describes. Unknown or malformed values are ignored, never an error, and
 * the combinations the app disallows are resolved the way the reducer resolves them: a verdict
 * map and % of normal both imply the harmonized source.
 */
export function selectionFromUrl(search: string): Selection {
  const params = new URLSearchParams(search)
  const area = areaFromText(params.get('area')) ?? WORLD
  const monthMatch = MONTH.exec(params.get('month') ?? '')
  const mapMode: MapMode = oneOf(params.get('map'), ['verdict', 'activity'] as const) ?? initialSelection.mapMode
  const valueMode: ValueMode = oneOf(params.get('value'), ['pct', 'activity'] as const) ?? initialSelection.valueMode
  let source: Source = oneOf(params.get('source'), ['raw', 'harmonized'] as const) ?? initialSelection.source
  if (mapMode === 'verdict' || valueMode === 'pct') source = 'harmonized'
  return {
    ...initialSelection,
    area,
    entity: area.entity_type === 'GLOBAL' ? null : area,
    month: monthMatch === null ? null : { year: Number(monthMatch[1]), month: Number(monthMatch[2]) },
    mapMode,
    source,
    valueMode,
  }
}
