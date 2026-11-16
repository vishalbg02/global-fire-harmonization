import { useEffect, useId, useRef, useState } from 'react'
import type { ButtonHTMLAttributes, PointerEvent } from 'react'
import { LONG_PRESS_MS, TIP_HOLD_MS } from './dockIcon.ts'

export type DockIconName = 'select' | 'layers' | 'globe' | 'satellite'

/** Line icons on a 20 px grid, drawn in the text colour: 1.5 px strokes, no fill. */
const PATHS: Record<DockIconName, string> = {
  // A dashed selection rectangle.
  select: 'M3 6V3h3M9 3h2M14 3h3v3M17 9v2M17 14v3h-3M11 17H9M6 17H3v-3M3 11V9',
  // Two stacked sheets.
  layers: 'M10 3 2.5 7 10 11l7.5-4L10 3ZM2.5 10.5 10 14.5l7.5-4M2.5 14 10 18l7.5-4',
  // A sphere with its equator and one meridian.
  globe: 'M10 2.5a7.5 7.5 0 1 0 0 15 7.5 7.5 0 0 0 0-15ZM2.5 10h15M10 2.5c-2.4 2-3.4 4.6-3.4 7.5s1 5.5 3.4 7.5c2.4-2 3.4-4.6 3.4-7.5s-1-5.5-3.4-7.5Z',
  // A satellite: a body between two solar panels, and its antenna.
  satellite: 'M8 7h4v5H8zM2 8h4v3H2zM14 8h4v3h-4zM6 9.5h2M12 9.5h2M10 12v3M7.5 17.5a2.5 2.5 0 0 1 5 0',
}

type Props = Omit<ButtonHTMLAttributes<HTMLButtonElement>, 'children' | 'aria-label' | 'aria-labelledby'> & {
  /** The visible label (on hover, focus and long-press), which is also the button's accessible name. */
  label: string
  icon: DockIconName
  'data-tour'?: string
}

/**
 * An icon button of the compact dock. Its label is a real element that names the button (aria-labelledby) and shows
 * on hover, on keyboard focus and after a long press on a touch screen. A long press shows the label only: the
 * button does not also act.
 */
export function DockIcon({ label, icon, onClick, className, ...rest }: Props) {
  const id = useId()
  const [tip, setTip] = useState(false)
  const timer = useRef<number | null>(null)
  const longPressed = useRef(false)

  const clear = () => {
    if (timer.current !== null) window.clearTimeout(timer.current)
    timer.current = null
  }
  useEffect(() => clear, [])
  useEffect(() => {
    if (!tip) return
    const t = window.setTimeout(() => setTip(false), TIP_HOLD_MS)
    return () => window.clearTimeout(t)
  }, [tip])

  const onPointerDown = (e: PointerEvent<HTMLButtonElement>) => {
    longPressed.current = false
    if (e.pointerType !== 'touch') return
    clear()
    timer.current = window.setTimeout(() => {
      longPressed.current = true
      setTip(true)
    }, LONG_PRESS_MS)
  }

  return (
    <span className="dock-icon-wrap">
      <button
        type="button"
        {...rest}
        className={className === undefined ? 'bare dock-icon' : `bare dock-icon ${className}`}
        aria-labelledby={`${id}-tip`}
        onPointerDown={onPointerDown}
        onPointerUp={clear}
        onPointerLeave={clear}
        onPointerCancel={clear}
        onContextMenu={(e) => {
          if (longPressed.current) e.preventDefault()
        }}
        onClick={(e) => {
          if (longPressed.current) {
            longPressed.current = false
            return
          }
          onClick?.(e)
        }}
      >
        <svg width="20" height="20" viewBox="0 0 20 20" aria-hidden="true" focusable="false">
          <path d={PATHS[icon]} fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
      </button>
      <span id={`${id}-tip`} className="dock-tip" data-shown={tip}>
        {label}
      </span>
    </span>
  )
}
