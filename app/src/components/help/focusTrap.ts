/** Keyboard focus inside the help's dialogs: what can take focus, and where Tab goes at the ends. */

export const FOCUSABLE =
  'a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), summary, [tabindex]:not([tabindex="-1"])'

/**
 * Where Tab goes inside a dialog with `count` focusable elements when element `index` has focus (-1: the dialog itself
 * or something outside the list). Returns the index to focus, or null to let the browser move focus normally.
 */
export function trapIndex(count: number, index: number, shift: boolean): number | null {
  if (count === 0) return null
  if (shift) return index <= 0 ? count - 1 : null
  return index === -1 || index >= count - 1 ? 0 : null
}

/** Keeps Tab and Shift+Tab inside `container`. Call it from the dialog's keydown handler. */
export function trapTab(container: HTMLElement, e: { key: string; shiftKey: boolean; preventDefault(): void }): void {
  if (e.key !== 'Tab') return
  const items = Array.from(container.querySelectorAll<HTMLElement>(FOCUSABLE)).filter((el) => el.getClientRects().length > 0)
  const active = document.activeElement
  const index = items.findIndex((el) => el === active)
  const to = trapIndex(items.length, index, e.shiftKey)
  if (to === null) return
  e.preventDefault()
  items[to]?.focus()
}

/** Where focus goes back to when the help closes: the control that opened it, else the Help button. */
export function returnFocusTarget(opener: Element | null, helpButton: Element | null, doc: { body: Element; contains(n: Node): boolean }): Element | null {
  if (opener !== null && opener !== doc.body && doc.contains(opener)) return opener
  return helpButton
}
