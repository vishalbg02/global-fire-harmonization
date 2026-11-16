import { describe, expect, it } from 'vitest'
import { SHEET_TEXTS, sheetHandleLabel } from '../../content/sheet.ts'
import {
  DRAG_SLOP,
  FLICK_SPEED,
  FULL_GAP,
  MIN_PEEK,
  clampDrag,
  nearestHeight,
  nextHeight,
  raiseTo,
  sheetHeights,
  snapAfterDrag,
} from './sheet.ts'

// SYNTHETIC viewport sizes (px), not data.
const H = sheetHeights(800, 800, 220)

describe('sheet heights', () => {
  it('are 90% and 50% of the viewport, and the measured peek', () => {
    expect(H).toEqual({ peek: 220, half: 400, full: 720 })
  })

  it('keep full within the space the sheet has, with a strip of the map in view', () => {
    expect(sheetHeights(800, 600, 200).full).toBe(600 - FULL_GAP)
  })

  it('keep the peek between the minimum and half', () => {
    expect(sheetHeights(800, 760, 10).peek).toBe(MIN_PEEK)
    expect(sheetHeights(800, 760, 700).peek).toBe(400)
  })

  it('stay ordered on a very short screen', () => {
    const s = sheetHeights(160, 120, 300)
    expect(s.peek).toBeLessThanOrEqual(s.half)
    expect(s.half).toBeLessThanOrEqual(s.full)
  })
})

describe('nearest height', () => {
  it('picks the closest of the three', () => {
    expect(nearestHeight(H, 250)).toBe('peek')
    expect(nearestHeight(H, 380)).toBe('half')
    expect(nearestHeight(H, 600)).toBe('full')
  })

  it('takes the lower one on a tie', () => {
    expect(nearestHeight(H, 310)).toBe('peek')
  })
})

describe('snapping after a drag', () => {
  it('treats a tiny move as a tap', () => {
    expect(snapAfterDrag(H, 220, 220 + DRAG_SLOP - 1, 0)).toBeNull()
  })

  it('settles on the nearest height after a slow drag', () => {
    expect(snapAfterDrag(H, 220, 450, 0.1)).toBe('half')
    expect(snapAfterDrag(H, 720, 650, -0.1)).toBe('full')
  })

  it('goes on to the next height after a flick', () => {
    expect(snapAfterDrag(H, 220, 240, FLICK_SPEED)).toBe('half')
    expect(snapAfterDrag(H, 400, 420, FLICK_SPEED + 1)).toBe('full')
    expect(snapAfterDrag(H, 720, 700, -FLICK_SPEED)).toBe('half')
    expect(snapAfterDrag(H, 400, 380, -2)).toBe('peek')
  })

  it('stays at the ends when flicked past them', () => {
    expect(snapAfterDrag(H, 700, 720, 3)).toBe('full')
    expect(snapAfterDrag(H, 240, 220, -3)).toBe('peek')
  })

  it('clamps a dragged height between peek and full', () => {
    expect(clampDrag(H, 50)).toBe(220)
    expect(clampDrag(H, 900)).toBe(720)
    expect(clampDrag(H, 500)).toBe(500)
  })
})

describe('keyboard cycle and raising', () => {
  it('cycles peek, half, full, peek', () => {
    expect(nextHeight('peek')).toBe('half')
    expect(nextHeight('half')).toBe('full')
    expect(nextHeight('full')).toBe('peek')
  })

  it('raises to half without lowering a full sheet', () => {
    expect(raiseTo('peek', 'half')).toBe('half')
    expect(raiseTo('half', 'half')).toBe('half')
    expect(raiseTo('full', 'half')).toBe('full')
  })
})

describe('sheet labels', () => {
  it('say the height now and the next one', () => {
    expect(sheetHandleLabel('peek', 'half')).toBe('Answer panel, short. Press to show it half height.')
  })

  it('claim nothing beyond the method and state no number', () => {
    const joined = SHEET_TEXTS.join(' ').toLowerCase()
    expect(joined).not.toMatch(/\bfires?\b/)
    expect(joined).not.toContain('burned area')
    expect(joined).not.toMatch(/\bcaus(e|ed|es)\b/)
    expect(joined).not.toMatch(/\bpredict|\bforecast|\baccura(cy|te)\b/)
    for (const t of SHEET_TEXTS) expect(t).not.toMatch(/\d/)
  })
})
