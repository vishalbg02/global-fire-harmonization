import { useCallback, useEffect, useId, useLayoutEffect, useRef, useState } from 'react'
import type { KeyboardEvent, PointerEvent, ReactNode } from 'react'
import { SHEET_LABEL, sheetHandleLabel } from '../../content/sheet.ts'
import { SHEET_ORDER, clampDrag, nextHeight, raiseTo, sheetHeights, snapAfterDrag } from './sheet.ts'
import type { SheetHeight, SheetHeights } from './sheet.ts'
import './sheet.css'

/** What the peek shows, at the latest: the big number, a state line, the skeleton, or the Start-here lede. */
const PEEK_TARGET = '.verdict .big, .summary .state, .summary-skeleton, .start-here-lede'
/** Space under the peek target, so its last line is not cut at the sheet's edge. */
const PEEK_PAD = 12

export interface BottomSheetProps {
  /** Always on screen at the top of the sheet, under the handle (the timeline). */
  top: ReactNode
  /** The answer panel; it scrolls inside the sheet at half and full height. */
  children: ReactNode
  /** Changes whenever an area or a story is chosen: the sheet then rises to at least half height. */
  raise: number
}

const setVar = (name: string, px: number | null) => {
  const style = document.documentElement.style
  if (px === null) style.removeProperty(name)
  else style.setProperty(name, `${Math.round(px)}px`)
}

/**
 * The answer panel as a bottom sheet over the map on narrow screens (T-093): a drag handle that snaps to three heights
 * (peek: the heading, verdict and big number; half; full), operable by keyboard (the handle is a button that cycles the
 * heights; the arrow keys step up and down). The map's overlays and the toast sit above the sheet through two CSS
 * variables: --sheet-h (the height now) and --sheet-rest (the same, at most half height).
 */
export function BottomSheet({ top, children, raise }: BottomSheetProps) {
  const id = useId()
  const sheetRef = useRef<HTMLDivElement>(null)
  const bodyRef = useRef<HTMLDivElement>(null)
  const [key, setKey] = useState<SheetHeight>('peek')
  const [heights, setHeights] = useState<SheetHeights | null>(null)
  const [dragH, setDragH] = useState<number | null>(null)
  const drag = useRef<{ startY: number; startH: number; samples: { y: number; t: number }[] } | null>(null)
  const suppressClick = useRef(false)

  // Measure the three heights, and where the first view starts (the header can wrap on a phone).
  const measure = useCallback(() => {
    const sheet = sheetRef.current
    const body = bodyRef.current
    const host = sheet?.parentElement
    if (!sheet || !body || !host) return
    const hostTop = host.getBoundingClientRect().top + window.scrollY
    setVar('--first-top', hostTop)
    const sheetTop = sheet.getBoundingClientRect().top
    const target = body.querySelector(PEEK_TARGET)
    const peek =
      target === null
        ? body.offsetTop + 160
        : target.getBoundingClientRect().bottom - sheetTop + body.scrollTop + PEEK_PAD
    setHeights(sheetHeights(window.innerHeight, host.clientHeight, peek))
  }, [])

  useLayoutEffect(() => {
    measure()
    const ro = new ResizeObserver(() => measure())
    if (bodyRef.current?.firstElementChild) ro.observe(bodyRef.current.firstElementChild)
    if (sheetRef.current?.parentElement) ro.observe(sheetRef.current.parentElement)
    const header = document.querySelector('.app-map .top')
    if (header) ro.observe(header)
    window.addEventListener('resize', measure)
    return () => {
      ro.disconnect()
      window.removeEventListener('resize', measure)
    }
  }, [measure])

  // A new area or story: rise to half (a full sheet stays full). The first render is not a choice.
  const firstRaise = useRef(raise)
  useEffect(() => {
    if (raise === firstRaise.current) return
    setKey((k) => raiseTo(k, 'half'))
  }, [raise])

  const h = dragH ?? (heights === null ? null : heights[key])

  useEffect(() => {
    if (h === null || heights === null) return
    setVar('--sheet-h', h)
    setVar('--sheet-rest', Math.min(h, heights.half))
  }, [h, heights])

  useEffect(
    () => () => {
      setVar('--sheet-h', null)
      setVar('--sheet-rest', null)
      setVar('--first-top', null)
    },
    [],
  )

  // Back to the top of the answer when the sheet goes down to its peek.
  useEffect(() => {
    if (key === 'peek' && bodyRef.current) bodyRef.current.scrollTop = 0
  }, [key])

  const onPointerDown = (e: PointerEvent<HTMLButtonElement>) => {
    if (heights === null || (e.pointerType === 'mouse' && e.button !== 0)) return
    e.currentTarget.setPointerCapture(e.pointerId)
    drag.current = { startY: e.clientY, startH: heights[key], samples: [{ y: e.clientY, t: e.timeStamp }] }
  }
  const onPointerMove = (e: PointerEvent<HTMLButtonElement>) => {
    const d = drag.current
    if (d === null || heights === null) return
    d.samples = [...d.samples.slice(-4), { y: e.clientY, t: e.timeStamp }]
    const moved = d.startY - e.clientY
    if (dragH !== null || Math.abs(moved) > 2) setDragH(clampDrag(heights, d.startH + moved))
  }
  const onPointerEnd = (e: PointerEvent<HTMLButtonElement>) => {
    const d = drag.current
    drag.current = null
    if (d === null || heights === null) return
    const first = d.samples[0]
    const dt = e.timeStamp - first.t
    const velocity = dt > 0 ? (first.y - e.clientY) / dt : 0
    const end = clampDrag(heights, d.startH + (d.startY - e.clientY))
    const snapped = e.type === 'pointercancel' ? key : snapAfterDrag(heights, d.startH, end, velocity)
    setDragH(null)
    if (snapped !== null) {
      suppressClick.current = true
      setKey(snapped)
    }
  }
  const onClick = () => {
    if (suppressClick.current) {
      suppressClick.current = false
      return
    }
    setKey(nextHeight)
  }
  const onKeyDown = (e: KeyboardEvent<HTMLButtonElement>) => {
    const i = SHEET_ORDER.indexOf(key)
    if (e.key === 'ArrowUp' && i < SHEET_ORDER.length - 1) setKey(SHEET_ORDER[i + 1])
    else if (e.key === 'ArrowDown' && i > 0) setKey(SHEET_ORDER[i - 1])
    else return
    e.preventDefault()
  }

  return (
    <div
      ref={sheetRef}
      className="sheet"
      role="region"
      aria-label={SHEET_LABEL}
      data-height={key}
      data-dragging={dragH !== null}
      style={h === null ? undefined : { height: h }}
    >
      <button
        type="button"
        className="bare sheet-handle"
        aria-expanded={key !== 'peek'}
        aria-controls={`${id}-body`}
        aria-label={sheetHandleLabel(key, nextHeight(key))}
        onClick={onClick}
        onKeyDown={onKeyDown}
        onPointerDown={onPointerDown}
        onPointerMove={onPointerMove}
        onPointerUp={onPointerEnd}
        onPointerCancel={onPointerEnd}
      >
        <span className="sheet-grip" aria-hidden="true" />
      </button>
      <div className="sheet-top">{top}</div>
      <div
        ref={bodyRef}
        id={`${id}-body`}
        className="sheet-body"
        onFocus={() => setKey((k) => raiseTo(k, 'half'))}
      >
        {children}
      </div>
    </div>
  )
}
