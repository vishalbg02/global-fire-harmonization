/**
 * The cell whose card is pinned on the map (T-071): set by a click, kept until it is dismissed
 * (close button or Esc), another cell is clicked, or the app selects something that is not that
 * cell. A hover tooltip is separate and unaffected. `null` means no card.
 */
export type PinnedCell = string | null

export type PinnedEvent =
  | { type: 'click'; cellId: string }
  | { type: 'dismiss' }
  | { type: 'selection'; selectedCellId: string | null }

export function pinnedReducer(state: PinnedCell, event: PinnedEvent): PinnedCell {
  switch (event.type) {
    case 'click':
      return event.cellId
    case 'dismiss':
      return null
    case 'selection':
      // The selection moved away from the pinned cell (an area chosen elsewhere): close the card.
      return state !== null && event.selectedCellId !== state ? null : state
  }
}
