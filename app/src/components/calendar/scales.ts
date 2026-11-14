import type { EntityMonth } from '../../api/contract.ts'
import { VERDICT_PRESENTATION } from '../../content/verdicts.ts'
import type { ValueMode } from '../../state/selection.ts'
import { sequentialColor } from '../map/scale.ts'

export type Rgb = readonly [number, number, number]

/** The % of normal ramp is clamped for colour at these values. Tooltips show the true value. */
export const PCT_LOW = 0
export const PCT_CENTRE = 100
export const PCT_HIGH = 200

// Okabe-Ito derived: blue for below, a near-white neutral at 100%, vermillion for above.
const BELOW: Rgb = [0, 114, 178]
const NEUTRAL: Rgb = [247, 247, 247]
const ABOVE: Rgb = [213, 94, 0]

export const NO_DATA_RGB: Rgb = [224, 224, 224]
export const OUTSIDE_RGB: Rgb = [255, 255, 255]

function mix(a: Rgb, b: Rgb, t: number): Rgb {
  return [
    Math.round(a[0] + (b[0] - a[0]) * t),
    Math.round(a[1] + (b[1] - a[1]) * t),
    Math.round(a[2] + (b[2] - a[2]) * t),
  ]
}

/** Diverging colour for % of normal, centred on 100% and clamped to 0% and 200%. */
export function divergingRgb(pct: number): Rgb {
  const v = Math.min(Math.max(pct, PCT_LOW), PCT_HIGH)
  return v < PCT_CENTRE
    ? mix(BELOW, NEUTRAL, (v - PCT_LOW) / (PCT_CENTRE - PCT_LOW))
    : mix(NEUTRAL, ABOVE, (v - PCT_CENTRE) / (PCT_HIGH - PCT_CENTRE))
}

export function sequentialRgb(value: number, max: number): Rgb {
  const [r, g, b] = sequentialColor(value, max)
  return [r, g, b]
}

export function toCss(rgb: Rgb): string {
  return `rgb(${rgb[0]}, ${rgb[1]}, ${rgb[2]})`
}

function channel(c: number): number {
  const s = c / 255
  return s <= 0.03928 ? s / 12.92 : ((s + 0.055) / 1.055) ** 2.4
}

/** WCAG 2.1 relative luminance. */
export function relativeLuminance(rgb: Rgb): number {
  return 0.2126 * channel(rgb[0]) + 0.7152 * channel(rgb[1]) + 0.0722 * channel(rgb[2])
}

/** WCAG 2.1 contrast ratio between two colours (1 to 21). */
export function contrastRatio(a: Rgb, b: Rgb): number {
  const la = relativeLuminance(a)
  const lb = relativeLuminance(b)
  return (Math.max(la, lb) + 0.05) / (Math.min(la, lb) + 0.05)
}

const BLACK: Rgb = [0, 0, 0]
const WHITE: Rgb = [255, 255, 255]

/** Black or white, whichever reads better on `background`. */
export function readableText(background: Rgb): Rgb {
  return contrastRatio(background, BLACK) >= contrastRatio(background, WHITE) ? BLACK : WHITE
}

export interface CellVisual {
  color: Rgb
  text: Rgb
  /** The verdict icon: shown with every record, so colour is never the only cue. */
  icon: string
  /** The value that colours the cell, or null (shown as "no data", never as zero). */
  value: number | null
}

/** Colour shows the value; the icon shows the verdict (both value modes). */
export function cellVisual(record: EntityMonth, mode: ValueMode, maxActivity: number): CellVisual {
  const value = mode === 'pct' ? record.pct_of_normal : record.estimate
  const color =
    value === null
      ? NO_DATA_RGB
      : mode === 'pct'
        ? divergingRgb(value)
        : sequentialRgb(value, maxActivity)
  return { color, text: readableText(color), icon: VERDICT_PRESENTATION[record.verdict].icon, value }
}
