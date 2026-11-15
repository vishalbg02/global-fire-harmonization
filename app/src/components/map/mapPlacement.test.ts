import { readFileSync } from 'node:fs'
import { describe, expect, it } from 'vitest'
import { CARD_FULL_WIDTH_PX, PLACEMENT, legendForcedCollapsed, tooltipCellId } from './mapPlacement.ts'

describe('hover tooltip vs pinned card', () => {
  it('shows the hovered cell, none when nothing is hovered', () => {
    expect(tooltipCellId('a', null, false)).toBe('a')
    expect(tooltipCellId('a', 'b', false)).toBe('a')
    expect(tooltipCellId(null, 'b', false)).toBeNull()
  })
  it('hides it for the pinned cell and while the pointer is over the card', () => {
    expect(tooltipCellId('a', 'a', false)).toBeNull()
    expect(tooltipCellId('a', 'b', true)).toBeNull()
  })
})

describe('legend and card never overlap', () => {
  it('collapses the legend on small screens only while a card is pinned', () => {
    expect(legendForcedCollapsed(true, 375)).toBe(true)
    expect(legendForcedCollapsed(true, CARD_FULL_WIDTH_PX)).toBe(true)
    expect(legendForcedCollapsed(true, 1280)).toBe(false)
    expect(legendForcedCollapsed(false, 375)).toBe(false)
  })

  it('keeps the card top right below the zoom buttons, in the CSS', () => {
    const css = readFileSync(new URL('./mapOverlays.css', import.meta.url), 'utf8')
    const rule = /\.map-pinned \{([^}]*)\}/.exec(css)?.[1] ?? ''
    expect(rule).toContain(`top: ${PLACEMENT.pinnedTopRem}rem`)
    expect(rule).toContain(`right: ${PLACEMENT.edgeRem}rem`)
    expect(rule).not.toMatch(/^\s*(bottom|left):/m)
    expect(rule).toContain(`${PLACEMENT.pinnedTopRem}rem - ${PLACEMENT.pinnedBottomRem}rem`)
    const legend = /\.map-legend \{([^}]*)\}/.exec(css)?.[1] ?? ''
    expect(legend).toMatch(/left: 0\.5rem/)
    expect(legend).toMatch(/bottom: 0\.5rem/)
  })
})
