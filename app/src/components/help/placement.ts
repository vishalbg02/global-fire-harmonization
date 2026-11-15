/**
 * Where a floating box (a coach mark, a "?" popover) goes beside the element it points at: on the first side where it
 * fits inside the viewport, moved along that side so it stays inside, with the arrow kept on the element. Pure
 * geometry for drawing; it prints nothing.
 */
export type Side = 'top' | 'right' | 'bottom' | 'left'

export interface Rect {
  top: number
  left: number
  width: number
  height: number
}

export interface Size {
  width: number
  height: number
}

export interface Placement {
  top: number
  left: number
  /** The side of the element the box sits on; null when there is no element (the box is centred). */
  side: Side | null
  /** The arrow's position along the box's edge that faces the element, in px from the box's start. */
  arrow: number
}

export interface PlaceOptions {
  /** The sides to try, in order. */
  order: readonly Side[]
  /** The space between the element and the box (the arrow sits in it). */
  gap?: number
  /** The least space between the box and the viewport's edge. */
  margin?: number
}

const clamp = (v: number, lo: number, hi: number) => (hi < lo ? lo : Math.min(Math.max(v, lo), hi))

/** The free space on each side of the element, inside the viewport. */
export function spaceAround(anchor: Rect, view: Size): Record<Side, number> {
  return {
    top: anchor.top,
    bottom: view.height - (anchor.top + anchor.height),
    left: anchor.left,
    right: view.width - (anchor.left + anchor.width),
  }
}

/** True when a box of this size fits on this side of the element. */
export function fits(side: Side, anchor: Rect, box: Size, view: Size, gap: number, margin: number): boolean {
  const space = spaceAround(anchor, view)[side]
  const vertical = side === 'top' || side === 'bottom'
  const need = (vertical ? box.height : box.width) + gap + margin
  const across = vertical ? box.width + 2 * margin <= view.width : box.height + 2 * margin <= view.height
  return space >= need && across
}

export function placeBeside(anchor: Rect | null, box: Size, view: Size, opts: PlaceOptions): Placement {
  const gap = opts.gap ?? 12
  const margin = opts.margin ?? 8
  if (anchor === null) {
    return {
      top: clamp((view.height - box.height) / 2, margin, view.height - box.height - margin),
      left: clamp((view.width - box.width) / 2, margin, view.width - box.width - margin),
      side: null,
      arrow: 0,
    }
  }
  const space = spaceAround(anchor, view)
  const side =
    opts.order.find((s) => fits(s, anchor, box, view, gap, margin)) ??
    // Nothing fits: the side with the most room, kept inside the viewport (it may then cover part of the element).
    [...opts.order].sort((a, b) => space[b] - space[a])[0] ??
    'bottom'
  // Centre on the part of the element that is on screen (a tall panel may run past the viewport).
  const cx = (Math.max(anchor.left, 0) + Math.min(anchor.left + anchor.width, view.width)) / 2
  const cy = (Math.max(anchor.top, 0) + Math.min(anchor.top + anchor.height, view.height)) / 2
  let top: number
  let left: number
  if (side === 'top' || side === 'bottom') {
    top = side === 'bottom' ? anchor.top + anchor.height + gap : anchor.top - gap - box.height
    left = cx - box.width / 2
  } else {
    left = side === 'right' ? anchor.left + anchor.width + gap : anchor.left - gap - box.width
    top = cy - box.height / 2
  }
  top = clamp(top, margin, view.height - box.height - margin)
  left = clamp(left, margin, view.width - box.width - margin)
  const vertical = side === 'top' || side === 'bottom'
  const edge = vertical ? box.width : box.height
  // The arrow points at the middle of the part of the element that is on screen.
  const arrow = clamp((vertical ? cx : cy) - (vertical ? left : top), 16, edge - 16)
  return { top, left, side, arrow }
}

/** The element's box grown by `pad` on every side and kept inside the viewport (for the highlight ring). */
export function ringRect(anchor: Rect, view: Size, pad = 4): Rect {
  const top = Math.max(anchor.top - pad, 2)
  const left = Math.max(anchor.left - pad, 2)
  const bottom = Math.min(anchor.top + anchor.height + pad, view.height - 2)
  const right = Math.min(anchor.left + anchor.width + pad, view.width - 2)
  return { top, left, width: Math.max(right - left, 0), height: Math.max(bottom - top, 0) }
}
