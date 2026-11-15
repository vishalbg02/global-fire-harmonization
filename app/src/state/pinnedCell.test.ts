import { describe, expect, it } from 'vitest'
import { pinnedReducer } from './pinnedCell.ts'
import type { PinnedCell, PinnedEvent } from './pinnedCell.ts'

const run = (events: PinnedEvent[], start: PinnedCell = null) => events.reduce(pinnedReducer, start)

describe('pinned cell card state', () => {
  it('opens on a click and stays through hover-like selection updates of the same cell', () => {
    expect(run([{ type: 'click', cellId: 'a' }])).toBe('a')
    expect(run([{ type: 'click', cellId: 'a' }, { type: 'selection', selectedCellId: 'a' }])).toBe('a')
  })

  it('another click replaces it', () => {
    expect(run([{ type: 'click', cellId: 'a' }, { type: 'click', cellId: 'b' }])).toBe('b')
  })

  it('is dismissed by Esc or the close button (dismiss), and dismissing nothing is harmless', () => {
    expect(run([{ type: 'click', cellId: 'a' }, { type: 'dismiss' }])).toBeNull()
    expect(run([{ type: 'dismiss' }])).toBeNull()
  })

  it('closes when the selection moves to something that is not the pinned cell', () => {
    expect(run([{ type: 'click', cellId: 'a' }, { type: 'selection', selectedCellId: null }])).toBeNull()
    expect(run([{ type: 'click', cellId: 'a' }, { type: 'selection', selectedCellId: 'c' }])).toBeNull()
  })

  it('does not open a card from a selection alone (a cell chosen by the link)', () => {
    expect(run([{ type: 'selection', selectedCellId: 'a' }])).toBeNull()
  })
})
