// The map's view choices (T-093): the shape (flat or globe), Satellite view and its day, and whether every verdict is
// drawn at full strength at world zoom. One state, owned by the app and kept in the link, so the control, the map's
// projection and the address bar cannot disagree. Display only: nothing here is a product value.
import { DEFAULT_SAT_DAY } from '../components/map/gibs.ts'

export type MapShape = 'flat' | 'globe'

export interface MapViewState {
  shape: MapShape
  satOn: boolean
  /** The day of the month wished for; the map clamps it to the days the month has. */
  satDay: number
  /** True when the three quiet verdicts are drawn at full strength at world zoom too. */
  showAll: boolean
}

export const SHOW_ALL_PARAM = 'allv'

/**
 * The view a link describes. `globe=1` is the globe; a link with other parameters and no `globe` keeps the flat map it
 * was shared with; an address with no parameters at all (a first visit at the world view) opens on the globe.
 */
export function mapViewFromSearch(search: string): MapViewState {
  const params = new URLSearchParams(search)
  const day = Number(params.get('satday'))
  const bare = Array.from(params.keys()).length === 0
  return {
    shape: params.get('globe') === '1' || bare ? 'globe' : 'flat',
    satOn: params.get('sat') === '1',
    satDay: Number.isInteger(day) && day >= 1 && day <= 31 ? day : DEFAULT_SAT_DAY,
    showAll: params.get(SHOW_ALL_PARAM) === '1',
  }
}

/** Writes the view into link parameters; the defaults (flat, no Satellite view, day 15, signal only) are left out. */
export function applyMapViewParams(params: URLSearchParams, view: MapViewState): void {
  params.delete('sat')
  params.delete('satday')
  params.delete('globe')
  params.delete(SHOW_ALL_PARAM)
  if (view.satOn) {
    params.set('sat', '1')
    if (view.satDay !== DEFAULT_SAT_DAY) params.set('satday', String(view.satDay))
  }
  if (view.shape === 'globe') params.set('globe', '1')
  if (view.showAll) params.set(SHOW_ALL_PARAM, '1')
}

export type MapViewAction =
  | { type: 'set-shape'; shape: MapShape }
  | { type: 'toggle-shape' }
  | { type: 'set-sat'; on: boolean }
  | { type: 'toggle-sat' }
  | { type: 'set-sat-day'; day: number }
  | { type: 'set-show-all'; on: boolean }

export function mapViewReducer(state: MapViewState, action: MapViewAction): MapViewState {
  switch (action.type) {
    case 'set-shape':
      return state.shape === action.shape ? state : { ...state, shape: action.shape }
    case 'toggle-shape':
      return { ...state, shape: state.shape === 'globe' ? 'flat' : 'globe' }
    case 'set-sat':
      return state.satOn === action.on ? state : { ...state, satOn: action.on }
    case 'toggle-sat':
      return { ...state, satOn: !state.satOn }
    case 'set-sat-day':
      return Number.isInteger(action.day) && action.day >= 1 && action.day <= 31 ? { ...state, satDay: action.day } : state
    case 'set-show-all':
      return state.showAll === action.on ? state : { ...state, showAll: action.on }
  }
}
