/**
 * Whether the globe hint is due: the shape has just changed from flat to globe (a user's choice; the first-visit globe
 * is the starting shape, not a change), the tour is not open, and the hint was not shown before in this browser.
 */
export function globeHintDue(from: 'flat' | 'globe', to: 'flat' | 'globe', suppressed: boolean, shownBefore: boolean): boolean {
  return from === 'flat' && to === 'globe' && !suppressed && !shownBefore
}
