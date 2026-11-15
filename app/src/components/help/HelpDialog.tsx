import { useEffect, useId, useRef } from 'react'
import type { ReactNode } from 'react'
import { createPortal } from 'react-dom'
import { HELP_CLOSE } from '../../content/help.ts'
import { HELP_BUTTON_ID } from '../layout/Header.tsx'
import { trapTab } from './focusTrap.ts'
import './help.css'

interface Props {
  title: string
  onClose: () => void
  /** 'sheet': the side sheet over the right of the page; 'small': a small panel. */
  kind: 'sheet' | 'small'
  children: ReactNode
}

/**
 * A modal dialog of the help: focus moves to it on open and stays inside it (Tab and Shift+Tab wrap), Esc and the
 * Close button close it, and so does a click outside it. The page is not dimmed, so the map stays in view.
 */
export function HelpDialog({ title, onClose, kind, children }: Props) {
  const id = useId()
  const ref = useRef<HTMLDivElement>(null)

  useEffect(() => {
    ref.current?.focus({ preventScroll: true })
  }, [])

  useEffect(() => {
    const onDown = (e: PointerEvent) => {
      const t = e.target
      if (!(t instanceof Element)) return
      // The Help button toggles the help itself; a "?" popover or another dialog is not "outside".
      if (ref.current?.contains(t) === true || t.closest(`#${HELP_BUTTON_ID}`) !== null) return
      onClose()
    }
    document.addEventListener('pointerdown', onDown)
    return () => document.removeEventListener('pointerdown', onDown)
  }, [onClose])

  return createPortal(
    <div
      ref={ref}
      className={`help-dialog help-dialog-${kind}`}
      role="dialog"
      aria-modal="true"
      aria-labelledby={`${id}-title`}
      tabIndex={-1}
      onKeyDown={(e) => {
        trapTab(e.currentTarget, e)
        if (e.key === 'Escape') {
          e.preventDefault()
          e.stopPropagation()
          onClose()
        }
      }}
    >
      <div className="help-dialog-head">
        <h2 id={`${id}-title`}>{title}</h2>
        <button type="button" className="btn btn-secondary help-close" onClick={onClose}>
          {HELP_CLOSE}
        </button>
      </div>
      <div className="help-dialog-body">{children}</div>
    </div>,
    document.body,
  )
}
