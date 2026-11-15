import type { SelectMode } from './MapModeSwitch.tsx'

/** The mode follows the two drawing flags of the app: none is Country (click to select). */
export function selectMode(drawing: boolean, polygonDrawing: boolean): SelectMode {
  return drawing ? 'rectangle' : polygonDrawing ? 'polygon' : 'country'
}
