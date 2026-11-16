/**
 * Labels of the bottom sheet and the compact map controls on narrow screens (T-093). Plain words; no numbers.
 */
import type { SheetHeight } from '../components/layout/sheet.ts'

/** How each height is said out loud. */
export const SHEET_HEIGHT_NAMES: Record<SheetHeight, string> = {
  peek: 'short',
  half: 'half height',
  full: 'full height',
}

/** The name of the drag handle: the height now and what pressing it does. */
export function sheetHandleLabel(current: SheetHeight, next: SheetHeight): string {
  return `Answer panel, ${SHEET_HEIGHT_NAMES[current]}. Press to show it ${SHEET_HEIGHT_NAMES[next]}.`
}

/** The region name of the sheet. */
export const SHEET_LABEL = 'Answer panel'

/** The compact dock's Flat / Globe button: what pressing it shows next. */
export const DOCK_SHOW_GLOBE = 'Show as a globe'
export const DOCK_SHOW_FLAT = 'Show as a flat map'

export const SHEET_TEXTS: readonly string[] = [
  ...Object.values(SHEET_HEIGHT_NAMES),
  sheetHandleLabel('peek', 'half'),
  sheetHandleLabel('half', 'full'),
  sheetHandleLabel('full', 'peek'),
  SHEET_LABEL,
  DOCK_SHOW_GLOBE,
  DOCK_SHOW_FLAT,
]
