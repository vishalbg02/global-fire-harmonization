import { useEffect, useId, useReducer, useRef } from 'react'
import { createPortal } from 'react-dom'
import {
  TOUR_BACK,
  TOUR_DONE,
  TOUR_LABEL,
  TOUR_MORE_HELP,
  TOUR_NEXT,
  TOUR_SKIP,
  TOUR_STEPS,
  tourCount,
} from '../../content/help.ts'
import { trapTab } from './focusTrap.ts'
import { TOUR_ORDER, tourAnchor, tourKey, tourReducer } from './tour.ts'
import type { TourAction, TourState } from './tour.ts'
import { useAnchoredBox } from './useAnchoredBox.ts'
import './help.css'

export interface TourProps {
  /** The tour closed (Skip, Esc or Done). */
  onClose: () => void
  /** "More help" on the last step: the Help sheet. */
  onMoreHelp: () => void
}

/**
 * The guided tour: five coach marks on the real interface. Each one rings its element (the map stays visible), sits
 * beside it inside the viewport with an arrow, and follows it on resize and scroll. Esc or Skip closes it at any step.
 */
export function Tour({ onClose, onMoreHelp }: TourProps) {
  const id = useId()
  const [state, dispatch] = useReducer((s: TourState, a: TourAction) => tourReducer(s, a), { step: 0 })
  const step = 'step' in state ? state.step : 0
  const current = TOUR_STEPS[step] ?? TOUR_STEPS[0]
  const box = useRef<HTMLDivElement>(null)
  const next = useRef<HTMLButtonElement>(null)

  useEffect(() => {
    if (!('step' in state)) onClose()
  }, [state, onClose])

  // Focus goes to Next (Done on the last step): entering the dialog reads its name, the count and the sentence, and
  // each new sentence is read from its live region. Enter then moves on.
  useEffect(() => {
    next.current?.focus({ preventScroll: true })
  }, [step])

  // The step's element, brought on screen first (on a phone the zones are stacked and the page scrolls).
  const { placement, ring } = useAnchoredBox(
    () => (current === undefined ? null : tourAnchor(current, document)),
    box,
    { order: current === undefined ? TOUR_ORDER.place : TOUR_ORDER[current.id], gap: 14, margin: 8 },
    step,
    (el) => {
      if (el instanceof HTMLElement) el.scrollIntoView({ block: 'nearest', inline: 'nearest' })
    },
  )
  if (current === undefined || !('step' in state)) return null
  const last = step === TOUR_STEPS.length - 1
  const style =
    placement === null
      ? { top: '0px', left: '0px', opacity: 0 }
      : { top: `${placement.top}px`, left: `${placement.left}px`, ['--arrow' as string]: `${placement.arrow}px` }

  return createPortal(
    <>
      {ring !== null && (
        <div
          key={`ring-${step}`}
          className="help-ring"
          aria-hidden="true"
          style={{ top: `${ring.top}px`, left: `${ring.left}px`, width: `${ring.width}px`, height: `${ring.height}px` }}
        />
      )}
      <div
        ref={box}
        className="help-coach"
        role="dialog"
        aria-modal="true"
        aria-label={TOUR_LABEL}
        aria-describedby={`${id}-count ${id}-title ${id}-text`}
        tabIndex={-1}
        data-side={placement?.side ?? 'none'}
        style={style}
        onKeyDown={(e) => {
          trapTab(e.currentTarget, e)
          const action = tourKey(e.key)
          if (action === null) return
          // The arrow keys stay with a focused button only for moving between steps, never for the page.
          e.preventDefault()
          e.stopPropagation()
          dispatch(action)
        }}
      >
        <div key={step} className="help-coach-body">
          <p id={`${id}-count`} className="help-coach-count">{tourCount(step, TOUR_STEPS.length)}</p>
          <h2 id={`${id}-title`} className="help-coach-title">
            {current.title}
          </h2>
          <p id={`${id}-text`} className="help-coach-text" aria-live="polite">
            {current.text}
          </p>
        </div>
        <div className="help-coach-actions">
          {last ? (
            <button type="button" className="bare help-link" onClick={onMoreHelp}>
              {TOUR_MORE_HELP}
            </button>
          ) : (
            <button type="button" className="bare help-link" onClick={() => dispatch({ type: 'skip' })}>
              {TOUR_SKIP}
            </button>
          )}
          <span className="help-coach-nav">
            {step > 0 && (
              <button type="button" className="btn btn-secondary" onClick={() => dispatch({ type: 'back' })}>
                {TOUR_BACK}
              </button>
            )}
            <button ref={next} type="button" className="btn btn-primary help-primary" onClick={() => dispatch({ type: 'next' })}>
              {last ? TOUR_DONE : TOUR_NEXT}
            </button>
          </span>
        </div>
        {placement?.side != null && <span className="help-arrow" aria-hidden="true" />}
      </div>
    </>,
    document.body,
  )
}
