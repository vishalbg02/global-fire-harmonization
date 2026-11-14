import { createContext, useContext } from 'react'
import type { Dispatch } from 'react'
import type { MapLayer } from '../api/contract.ts'

/** An area the calendar can show: the series endpoint serves these entity types. */
export interface Area {
  entity_type: 'COUNTRY' | 'CONTINENT' | 'GLOBAL'
  entity_id: string
  entity_name: string
}

export interface SelectedEntity {
  entity_type: 'CELL' | Area['entity_type']
  entity_id: string
  entity_name: string
}

/** What the calendar colours by. Raw versus harmonized is a separate control (T-033). */
export type ValueMode = 'pct' | 'activity'

export const WORLD: Area = { entity_type: 'GLOBAL', entity_id: 'GLOBAL', entity_name: 'World' }

export interface Selection {
  entity: SelectedEntity | null
  /**
   * The area the calendar shows: the last selected country, continent or the world.
   * Selecting a cell leaves it unchanged (cells have no series); clearing resets to the world.
   */
  area: Area
  /** null until the available months are known. */
  month: { year: number; month: number } | null
  layer: MapLayer
  valueMode: ValueMode
}

export type SelectionAction =
  | { type: 'select-entity'; entity: SelectedEntity }
  | { type: 'clear-entity' }
  | { type: 'set-month'; year: number; month: number }
  | { type: 'set-layer'; layer: MapLayer }
  | { type: 'set-value-mode'; valueMode: ValueMode }

export const initialSelection: Selection = {
  entity: null,
  area: WORLD,
  month: null,
  layer: 'verdict',
  valueMode: 'pct',
}

export function selectionReducer(state: Selection, action: SelectionAction): Selection {
  switch (action.type) {
    case 'select-entity': {
      const { entity } = action
      if (entity.entity_type === 'CELL') return { ...state, entity }
      return { ...state, entity, area: { ...entity, entity_type: entity.entity_type } }
    }
    case 'clear-entity':
      return { ...state, entity: null, area: WORLD }
    case 'set-month':
      return { ...state, month: { year: action.year, month: action.month } }
    case 'set-layer':
      return { ...state, layer: action.layer }
    case 'set-value-mode':
      return { ...state, valueMode: action.valueMode }
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
