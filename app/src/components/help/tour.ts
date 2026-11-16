import { TOUR_STEPS } from '../../content/help.ts'
import type { TourAnchor, TourStep } from '../../content/help.ts'
import type { Side } from './placement.ts'

/** The tour's position: the step shown, or closed. */
export type TourState = { step: number } | { closed: 'skipped' | 'finished' }

export type TourAction = { type: 'next' } | { type: 'back' } | { type: 'skip' }

/** Next on the last step finishes the tour; Back on the first step stays; Skip (and Esc) close it at any step. */
export function tourReducer(state: TourState, action: TourAction, total: number = TOUR_STEPS.length): TourState {
  if (!('step' in state)) return state
  switch (action.type) {
    case 'next':
      return state.step + 1 >= total ? { closed: 'finished' } : { step: state.step + 1 }
    case 'back':
      return { step: Math.max(state.step - 1, 0) }
    case 'skip':
      return { closed: 'skipped' }
  }
}

/** The tour's own keys inside the coach mark: Esc closes, the arrow keys go back and forward. Null for any other key. */
export function tourKey(key: string): TourAction | null {
  if (key === 'Escape') return { type: 'skip' }
  if (key === 'ArrowRight') return { type: 'next' }
  if (key === 'ArrowLeft') return { type: 'back' }
  return null
}

/**
 * The sides to try for each step's coach mark: beside the dock's controls, above the timeline, to the left of the
 * answer panel. On a phone none of the sides fit and the first one with room below or above is used.
 */
export const TOUR_ORDER: Readonly<Record<TourAnchor, readonly Side[]>> = {
  place: ['right', 'bottom', 'top', 'left'],
  month: ['top', 'bottom', 'right', 'left'],
  verdict: ['left', 'bottom', 'top', 'right'],
  why: ['left', 'bottom', 'top', 'right'],
  raw: ['right', 'bottom', 'top', 'left'],
}

/** A selector for one `data-tour` anchor. */
export const tourSelector = (id: string) => `[data-tour="${id}"]`

interface Finder {
  querySelector(selector: string): Element | null
}

/** True when an element takes up space on the page (a hidden or collapsed one has an empty box). */
const shown = (el: Element): boolean => {
  if (typeof (el as HTMLElement).getBoundingClientRect !== 'function') return true
  const r = el.getBoundingClientRect()
  return r.width > 0 || r.height > 0
}

/** The element a step points at: its own anchor, else its fallback, else null (the coach mark is then centred). */
export function tourAnchor(step: TourStep, doc: Finder): Element | null {
  for (const id of [step.id, step.fallback]) {
    if (id === undefined) continue
    const el = doc.querySelector(tourSelector(id))
    if (el !== null && shown(el)) return el
  }
  return null
}
