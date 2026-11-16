import { useLayoutEffect, useRef, useState } from 'react'
import type { RefObject } from 'react'
import { placeBeside, ringRect } from './placement.ts'
import type { PlaceOptions, Placement, Rect } from './placement.ts'

export interface AnchoredBox {
  placement: Placement | null
  /** The highlight ring around the element, or null without one. */
  ring: Rect | null
}

const sameRect = (a: Rect | null, b: Rect | null) =>
  a === b || (a !== null && b !== null && a.top === b.top && a.left === b.left && a.width === b.width && a.height === b.height)

/**
 * Keeps a fixed-position box beside an element: measured after render and again on resize, on any scroll (the answer
 * panel and the page scroll on their own) and when either box changes size. `getAnchor` finds the element (null for a
 * centred box); it is asked again whenever `key` changes, and `onAnchor` is told which element it found.
 */
export function useAnchoredBox(
  getAnchor: () => Element | null,
  box: RefObject<HTMLElement | null>,
  opts: PlaceOptions,
  key: unknown,
  onAnchor?: (el: Element | null) => void,
): AnchoredBox {
  const [state, setState] = useState<AnchoredBox>({ placement: null, ring: null })
  const order = opts.order.join(',')
  const { gap, margin } = opts
  const find = useRef(getAnchor)
  const found = useRef(onAnchor)
  useLayoutEffect(() => {
    find.current = getAnchor
    found.current = onAnchor
  })
  useLayoutEffect(() => {
    const anchor = find.current()
    found.current?.(anchor)
    let frame = 0
    const measure = () => {
      frame = 0
      const el = box.current
      if (el === null) return
      const view = { width: document.documentElement.clientWidth, height: window.innerHeight }
      const size = { width: el.offsetWidth, height: el.offsetHeight }
      const a = anchor?.getBoundingClientRect() ?? null
      const rect = a === null ? null : { top: a.top, left: a.left, width: a.width, height: a.height }
      const placement = placeBeside(rect, size, view, { order: order.split(',') as PlaceOptions['order'], gap, margin })
      const ring = rect === null ? null : ringRect(rect, view)
      setState((prev) =>
        prev.placement !== null &&
        prev.placement.top === placement.top &&
        prev.placement.left === placement.left &&
        prev.placement.side === placement.side &&
        prev.placement.arrow === placement.arrow &&
        sameRect(prev.ring, ring)
          ? prev
          : { placement, ring },
      )
    }
    const schedule = () => {
      if (frame === 0) frame = requestAnimationFrame(measure)
    }
    measure()
    window.addEventListener('resize', schedule)
    window.addEventListener('scroll', schedule, true)
    const observer = typeof ResizeObserver === 'function' ? new ResizeObserver(schedule) : null
    if (observer !== null) {
      if (box.current !== null) observer.observe(box.current)
      if (anchor !== null) observer.observe(anchor)
    }
    return () => {
      if (frame !== 0) cancelAnimationFrame(frame)
      window.removeEventListener('resize', schedule)
      window.removeEventListener('scroll', schedule, true)
      observer?.disconnect()
    }
  }, [box, order, gap, margin, key])
  return state
}
