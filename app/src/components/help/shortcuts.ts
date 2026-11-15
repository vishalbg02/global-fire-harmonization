import type { ShortcutId } from '../../content/help.ts'

/**
 * The keyboard shortcuts of the map page (T-093) as a pure map from a key press to an action, with the guard that keeps
 * them out of the way: nothing while the user types, while Ctrl, Alt or Cmd is held, or inside a dialog (except Esc);
 * the arrow keys stay with the map and the sliders when they have focus, and Space stays with any focused control.
 */

/** The parts of a focused element the guard looks at (an HTMLElement has them all). */
export interface KeyTarget {
  tagName: string
  isContentEditable?: boolean
  getAttribute(name: string): string | null
  closest?(selector: string): unknown
}

export interface KeyPress {
  key: string
  ctrlKey: boolean
  metaKey: boolean
  altKey: boolean
  defaultPrevented?: boolean
  target: KeyTarget | null
}

const KEYS: Readonly<Record<string, ShortcutId>> = {
  ArrowLeft: 'month-prev',
  ArrowRight: 'month-next',
  PageDown: 'year-prev',
  PageUp: 'year-next',
  ' ': 'play',
  g: 'globe',
  G: 'globe',
  s: 'satellite',
  S: 'satellite',
  '/': 'search',
  '?': 'shortcuts',
  Escape: 'close',
}

/** The key that each action answers to, for the tests and the sheet. */
export const SHORTCUT_KEYS: Readonly<Record<string, ShortcutId>> = KEYS

const within = (t: KeyTarget, selector: string): boolean => typeof t.closest === 'function' && t.closest(selector) !== null

/** True while the user types: a text field, a list box, a select or an editable region has focus. */
export function isTypingTarget(t: KeyTarget | null): boolean {
  if (t === null) return false
  const tag = t.tagName.toUpperCase()
  if (tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT') return true
  if (t.isContentEditable === true) return true
  const editable = t.getAttribute('contenteditable')
  if (editable !== null && editable !== 'false') return true
  const role = t.getAttribute('role')
  return role === 'textbox' || role === 'combobox' || role === 'searchbox' || role === 'spinbutton'
}

/** Controls that use the arrow keys themselves: the map canvas, sliders, tabs, radio groups, lists and grids. */
const ARROW_ROLES = new Set(['slider', 'tab', 'radio', 'option', 'listbox', 'menuitem', 'menu', 'grid', 'gridcell', 'tree', 'treeitem'])
export function ownsArrows(t: KeyTarget | null): boolean {
  if (t === null) return false
  if (t.tagName.toUpperCase() === 'CANVAS') return true
  const role = t.getAttribute('role')
  if (role !== null && ARROW_ROLES.has(role)) return true
  return within(t, '.maplibregl-canvas-container') || within(t, '[role="slider"]')
}

/** Controls that Space activates: buttons, links, switches, check boxes, summaries. */
const SPACE_TAGS = new Set(['BUTTON', 'A', 'SUMMARY'])
const SPACE_ROLES = new Set(['button', 'switch', 'checkbox', 'radio', 'tab', 'link', 'menuitem', 'option', 'slider', 'treeitem', 'gridcell'])
export function ownsSpace(t: KeyTarget | null): boolean {
  if (t === null) return false
  if (SPACE_TAGS.has(t.tagName.toUpperCase())) return true
  const role = t.getAttribute('role')
  return role !== null && SPACE_ROLES.has(role)
}

/** The action of a key press, or null when the press belongs to something else. */
export function shortcutFor(e: KeyPress): ShortcutId | null {
  const id = KEYS[e.key]
  if (id === undefined) return null
  if (e.ctrlKey || e.metaKey || e.altKey) return null
  if (id === 'close') return 'close'
  if (e.defaultPrevented === true) return null
  const t = e.target
  if (isTypingTarget(t)) return null
  if (t !== null && within(t, '[role="dialog"]')) return null
  if ((id === 'month-prev' || id === 'month-next' || id === 'year-prev' || id === 'year-next') && ownsArrows(t)) return null
  if (id === 'play' && ownsSpace(t)) return null
  return id
}

/** Mac keyboards zoom the map with Cmd + scroll; the others with Ctrl + scroll. */
export function isMacPlatform(platform: string): boolean {
  return /mac|iphone|ipad|ipod/i.test(platform)
}
