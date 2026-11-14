import { createContext, useContext } from 'react'
import type { Dispatch } from 'react'
import type { Bbox, MapLayer } from '../api/contract.ts'

/** A country, a continent or the world: the series endpoint serves these. */
export interface PresetArea {
  entity_type: 'COUNTRY' | 'CONTINENT' | 'GLOBAL'
  entity_id: string
  entity_name: string
}

/** A rectangle chosen by the user; its series comes from `POST /api/series/custom`. */
export interface CustomArea {
  entity_type: 'CUSTOM'
  entity_id: string
  entity_name: string
  bbox: Bbox
}

/** An area the calendar and the evidence panel can show. */
export type Area = PresetArea | CustomArea

export type SelectedEntity = Area | { entity_type: 'CELL'; entity_id: string; entity_name: string }

/** Asks the map to fit a box. A new object each time, so the same box can be requested again. */
export interface FitRequest {
  bbox: Bbox
}

/** The default view when the world is chosen. */
export const WORLD_BBOX: Bbox = [-180, -60, 180, 75]

/** What the calendar colours by. */
export type ValueMode = 'pct' | 'activity'

/**
 * Which stored value the activity views show: the raw combined count (`raw_combined_cell_days`)
 * or the harmonized estimate (`estimate`). One shared choice for the calendar and the map.
 */
export type Source = 'raw' | 'harmonized'

/** The map shows the verdict (always harmonized) or the activity of the chosen source. */
export type MapMode = 'verdict' | 'activity'

export const WORLD: PresetArea = { entity_type: 'GLOBAL', entity_id: 'GLOBAL', entity_name: 'World' }

export interface Selection {
  entity: SelectedEntity | null
  /**
   * The area the calendar shows: the last selected country, continent or the world.
   * Selecting a cell leaves it unchanged (cells have no series); clearing resets to the world.
   */
  area: Area
  /** The last request to fit the map to an area chosen in the area picker (null at start). */
  fit: FitRequest | null
  /** null until the available months are known. */
  month: { year: number; month: number } | null
  mapMode: MapMode
  source: Source
  valueMode: ValueMode
}

export type SelectionAction =
  | { type: 'select-entity'; entity: SelectedEntity; fit?: Bbox }
  | { type: 'clear-entity' }
  | { type: 'set-month'; year: number; month: number }
  | { type: 'set-map-mode'; mapMode: MapMode }
  | { type: 'set-source'; source: Source }
  | { type: 'set-value-mode'; valueMode: ValueMode }

export const initialSelection: Selection = {
  entity: null,
  area: WORLD,
  fit: null,
  month: null,
  mapMode: 'verdict',
  source: 'harmonized',
  valueMode: 'pct',
}

/** The `layer` value to request from GET /api/map for the current selection. */
export function effectiveLayer(selection: Pick<Selection, 'mapMode' | 'source'>): MapLayer {
  return selection.mapMode === 'verdict' ? 'verdict' : selection.source
}

/** Raw has no baseline in the contract, so it is unavailable in % of normal mode. */
export function rawAvailable(valueMode: ValueMode): boolean {
  return valueMode !== 'pct'
}

export function selectionReducer(state: Selection, action: SelectionAction): Selection {
  switch (action.type) {
    case 'select-entity': {
      const { entity, fit } = action
      const fitRequest = fit === undefined ? state.fit : { bbox: fit }
      if (entity.entity_type === 'CELL') return { ...state, entity }
      return { ...state, entity, area: entity, fit: fitRequest }
    }
    case 'clear-entity':
      return { ...state, entity: null, area: WORLD, fit: { bbox: WORLD_BBOX } }
    case 'set-month':
      return { ...state, month: { year: action.year, month: action.month } }
    case 'set-map-mode':
      // A verdict exists only for the harmonized estimate, so Verdict implies Harmonized.
      return action.mapMode === 'verdict'
        ? { ...state, mapMode: 'verdict', source: 'harmonized' }
        : { ...state, mapMode: 'activity' }
    case 'set-source':
      if (action.source === 'harmonized') return { ...state, source: 'harmonized' }
      // Raw is refused in % of normal mode; choosing Raw on the verdict map moves it to Activity.
      if (!rawAvailable(state.valueMode)) return state
      return { ...state, source: 'raw', mapMode: 'activity' }
    case 'set-value-mode':
      // % of normal exists only for harmonized data, so it implies Harmonized.
      return action.valueMode === 'pct'
        ? { ...state, valueMode: 'pct', source: 'harmonized' }
        : { ...state, valueMode: 'activity' }
  }
}

export const SelectionContext = createContext<{
  selection: Selection
  dispatch: Dispatch<SelectionAction>
} | null>(null)

export function useSelection() {
  const ctx = useContext(SelectionContext)
  if (ctx === null) throw new Error('useSelection must be used inside SelectionContext.Provider')
  return ctx
}
