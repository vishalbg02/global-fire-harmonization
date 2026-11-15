import { useCallback, useEffect, useId, useRef, useState } from 'react'
import { createPortal } from 'react-dom'
import { EXPLAINERS, EXPLAINER_LEARN_MORE, explainerLabel } from '../../content/help.ts'
import type { ExplainerId } from '../../content/help.ts'
import { methodsHref } from '../../content/methodsLink.ts'
import { useAnchoredBox } from './useAnchoredBox.ts'
import './help.css'

// Only one explainer is open at a time: opening one closes the one before.
let closeOpen: (() => void) | null = null

/**
 * A small "?" next to a term: opens one or two sentences from the approved plain-language texts, with a link to the
 * methods page. Placed where the term appears (the answer panel, the dock, the timeline, the legend). The popover is
 * drawn on the page's top layer (a portal), so a parent that clips its content does not cut it off.
 */
export function HelpTip({ term }: { term: ExplainerId }) {
  const entry = EXPLAINERS[term]
  const id = useId()
  const [open, setOpen] = useState(false)
  const button = useRef<HTMLButtonElement>(null)
  const pop = useRef<HTMLDivElement>(null)

  const close = useCallback((refocus: boolean) => {
    setOpen(false)
    if (refocus) button.current?.focus()
  }, [])

  useEffect(() => {
    if (!open) return
    const mine = () => close(false)
    if (closeOpen !== null && closeOpen !== mine) closeOpen()
    closeOpen = mine
    pop.current?.focus({ preventScroll: true })
    const onDown = (e: PointerEvent) => {
      const t = e.target
      if (!(t instanceof Node)) return
      if (pop.current?.contains(t) === true || button.current?.contains(t) === true) return
      // Focus goes back to the "?" only when it was inside the popover; a click on another control keeps its focus.
      close(pop.current?.contains(document.activeElement) === true)
    }
    const onKey = (e: KeyboardEvent) => {
      if (e.key !== 'Escape') return
      e.preventDefault()
      e.stopPropagation()
      close(true)
    }
    document.addEventListener('pointerdown', onDown)
    document.addEventListener('keydown', onKey, true)
    return () => {
      if (closeOpen === mine) closeOpen = null
      document.removeEventListener('pointerdown', onDown)
      document.removeEventListener('keydown', onKey, true)
    }
  }, [open, close])

  const { placement } = useAnchoredBox(() => (open ? button.current : null), pop, { order: ['bottom', 'top', 'right', 'left'], gap: 8, margin: 8 }, open)
  const style =
    placement === null
      ? { top: '0px', left: '0px', opacity: 0 }
      : { top: `${placement.top}px`, left: `${placement.left}px`, ['--arrow' as string]: `${placement.arrow}px` }

  return (
    <>
      <button
        ref={button}
        type="button"
        className="bare help-tip"
        aria-label={explainerLabel(entry.term)}
        aria-expanded={open}
        aria-controls={open ? `${id}-pop` : undefined}
        onClick={() => (open ? close(false) : setOpen(true))}
      >
        <span className="help-tip-glyph" aria-hidden="true">
          ?
        </span>
      </button>
      {open &&
        createPortal(
          <div
            ref={pop}
            id={`${id}-pop`}
            className="help-pop"
            role="dialog"
            aria-labelledby={`${id}-term`}
            aria-describedby={`${id}-text`}
            tabIndex={-1}
            data-side={placement?.side ?? 'none'}
            style={style}
            // The popover is drawn elsewhere on the page, but React passes its events up to the "?"'s parents: keep
            // its clicks from reaching them (a row or a summary that the "?" sits in).
            onClick={(e) => e.stopPropagation()}
            onPointerDown={(e) => e.stopPropagation()}
            onKeyDown={(e) => {
              e.stopPropagation()
              // Tab past either end of the popover returns to the "?", where the page's own order goes on.
              if (e.key !== 'Tab') return
              const link = pop.current?.querySelector('a')
              const atEnd = e.shiftKey ? document.activeElement === pop.current : document.activeElement === link
              if (atEnd) {
                e.preventDefault()
                close(true)
              }
            }}
          >
            <p className="help-pop-term" id={`${id}-term`}>
              <strong>{entry.term}</strong>
            </p>
            <p className="help-pop-text" id={`${id}-text`}>
              {entry.text}
            </p>
            <a className="help-pop-more" href={methodsHref(entry.anchor)}>
              {EXPLAINER_LEARN_MORE}
            </a>
            {placement?.side != null && <span className="help-arrow" aria-hidden="true" />}
          </div>,
          document.body,
        )}
    </>
  )
}
