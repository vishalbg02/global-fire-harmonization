/**
 * The answer panel's bottom sheet on narrow screens (T-093): three heights, the snapping after a drag and the keyboard
 * cycle. Pure functions; the component (BottomSheet.tsx) measures and draws.
 */

export type SheetHeight = 'peek' | 'half' | 'full'

export const SHEET_ORDER: readonly SheetHeight[] = ['peek', 'half', 'full']

/** At or below this width the answer panel is a bottom sheet over the map (tablets, phones). */
export const SHEET_QUERY = '(max-width: 900px)'

/** A pointer that moves less than this (px) between down and up is a tap on the handle, not a drag. */
export const DRAG_SLOP = 6
/** A release faster than this (px per ms) is a flick: the sheet goes on to the next height in that direction. */
export const FLICK_SPEED = 0.5
/** The peek never gets smaller than this (the handle and a line of text). */
export const MIN_PEEK = 96
/** At full height a strip of the map this tall (px) stays in view, so it is clear the sheet lies over the map. */
export const FULL_GAP = 40

export type SheetHeights = Record<SheetHeight, number>

/**
 * The three heights in px. Full is 90% of the viewport and half 50%, both within the space the sheet has less
 * FULL_GAP; peek is the measured height of the first view of the content (heading, verdict and big number), kept between MIN_PEEK and half.
 */
export function sheetHeights(viewport: number, available: number, peekContent: number): SheetHeights {
  const full = Math.max(0, Math.round(Math.min(viewport * 0.9, available - FULL_GAP)))
  const half = Math.min(Math.round(viewport * 0.5), full)
  const peek = Math.min(Math.max(Math.round(peekContent), Math.min(MIN_PEEK, half)), half)
  return { peek, half, full }
}

/** The height whose px value is closest to `h` (the lower one on a tie). */
export function nearestHeight(heights: SheetHeights, h: number): SheetHeight {
  let best: SheetHeight = 'peek'
  for (const key of SHEET_ORDER) {
    if (Math.abs(heights[key] - h) < Math.abs(heights[best] - h)) best = key
  }
  return best
}

/** The next height of the keyboard cycle: peek, half, full, then peek again. */
export function nextHeight(current: SheetHeight): SheetHeight {
  return SHEET_ORDER[(SHEET_ORDER.indexOf(current) + 1) % SHEET_ORDER.length]
}

/** Raise to at least `to`; a taller sheet stays as it is. */
export function raiseTo(current: SheetHeight, to: SheetHeight): SheetHeight {
  return SHEET_ORDER.indexOf(current) >= SHEET_ORDER.indexOf(to) ? current : to
}

/** A dragged height, kept between the peek and the full height. */
export function clampDrag(heights: SheetHeights, h: number): number {
  return Math.min(Math.max(h, heights.peek), heights.full)
}

/**
 * Where the sheet settles after a drag from `startH` to `endH` px, released at `velocity` px/ms (positive = upwards).
 * Returns null when the pointer barely moved (a tap: the caller cycles instead). A flick goes to the next height in
 * its direction; otherwise the nearest height wins.
 */
export function snapAfterDrag(heights: SheetHeights, startH: number, endH: number, velocity: number): SheetHeight | null {
  if (Math.abs(endH - startH) < DRAG_SLOP) return null
  if (Math.abs(velocity) >= FLICK_SPEED) {
    const up = velocity > 0
    const candidates = SHEET_ORDER.filter((k) => (up ? heights[k] > endH : heights[k] < endH))
    if (candidates.length > 0) return up ? candidates[0] : candidates[candidates.length - 1]
    return up ? 'full' : 'peek'
  }
  return nearestHeight(heights, endH)
}
