import { createContext, useContext } from 'react'
import type { Dispatch } from 'react'
import type { MapLayer } from '../api/contract.ts'

export interface SelectedEntity {
  entity_type: 'CELL' | 'COUNTRY'
  entity_id: string
  entity_name: string
}

export interface Selection {
  entity: SelectedEntity | null
  /** null until the available months are known. */
  month: { year: number; month: number } | null
  layer: MapLayer
}

export type SelectionAction =
  | { type: 'select-entity'; entity: SelectedEntity }
  | { type: 'clear-entity' }
  | { type: 'set-month'; year: number; month: number }
  | { type: 'set-layer'; layer: MapLayer }

export const initialSelection: Selection = { entity: null, month: null, layer: 'verdict' }

export function selectionReducer(state: Selection, action: SelectionAction): Selection {
  switch (action.type) {
    case 'select-entity':
      return { ...state, entity: action.entity }
    case 'clear-entity':
      return { ...state, entity: null }
    case 'set-month':
      return { ...state, month: { year: action.year, month: action.month } }
    case 'set-layer':
      return { ...state, layer: action.layer }
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
