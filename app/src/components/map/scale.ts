import type { MapCell, MapLayer } from '../../api/contract.ts'
import { VERDICT_PRESENTATION } from '../../content/verdicts.ts'

export type Rgb = readonly [number, number, number]
export type Rgba = readonly [number, number, number, number]

/** Fill for cells whose value is null: a distinct neutral, never the low end of the ramp. */
export const NO_DATA_COLOR: Rgba = [235, 235, 235, 200]

// Perceptually ordered, colour-blind-safe sequential ramp (viridis stops).
const RAMP: readonly Rgb[] = [
  [68, 1, 84],
  [59, 82, 139],
  [33, 145, 140],
  [94, 201, 98],
  [253, 231, 37],
]

/** Colour for `value` on a ramp from 0 to `max`. Null (or a non-positive max) is "no data". */
export function sequentialColor(value: number | null, max: number): Rgba {
  if (value === null || !(max > 0)) return NO_DATA_COLOR
  const t = Math.min(Math.max(value / max, 0), 1)
  const scaled = t * (RAMP.length - 1)
  const i = Math.min(Math.floor(scaled), RAMP.length - 2)
  const f = scaled - i
  const a = RAMP[i]
  const b = RAMP[i + 1]
  return [
    Math.round(a[0] + (b[0] - a[0]) * f),
    Math.round(a[1] + (b[1] - a[1]) * f),
    Math.round(a[2] + (b[2] - a[2]) * f),
    210,
  ]
}

/** The value shown for a cell in raw or harmonized mode (null stays null). */
export function layerValue(cell: MapCell, layer: Exclude<MapLayer, 'verdict'>): number | null {
  return layer === 'raw' ? cell.raw_combined_cell_days : cell.estimate
}

/**
 * One maximum shared by the Raw and Harmonized modes so the two are comparable on the
 * same scale. Computed over both values for every cell; returns 0 if there are none.
 */
export function sharedMax(cells: readonly MapCell[]): number {
  let max = 0
  for (const c of cells) {
    max = Math.max(max, c.raw_combined_cell_days, c.estimate ?? 0)
  }
  return max
}

/**
 * Cells whose meaning must not rest on a pale fill alone: "no detected activity" in the verdict
 * layer and a null value in the activity layers ("no data"). They get a dark outline (T-042).
 */
export function needsOutline(cell: MapCell, layer: MapLayer): boolean {
  return layer === 'verdict' ? cell.verdict === 'NO_DETECTED_ACTIVITY' : layerValue(cell, layer) === null
}

export function cellFillColor(cell: MapCell, layer: MapLayer, max: number): Rgba {
  if (layer === 'verdict') {
    const [r, g, b] = VERDICT_PRESENTATION[cell.verdict].color
    return [r, g, b, 220]
  }
  return sequentialColor(layerValue(cell, layer), max)
}
