/** The id of the toolbar button that opens the draw panel: focus returns to it when Esc closes the panel (T-074). */
export const DRAW_MENU_BUTTON_ID = 'draw-menu-button'

/**
 * Moves keyboard focus to the element with this id after the next paint. A panel that closes removes the
 * element that had focus, which would leave focus on the page body; callers hand focus back to the control
 * that opened the panel. Does nothing when the element is not there.
 */
export function focusLater(id: string, doc: Document = document): void {
  const run = () => doc.getElementById(id)?.focus()
  if (typeof requestAnimationFrame === 'function') requestAnimationFrame(run)
  else setTimeout(run, 0)
}
