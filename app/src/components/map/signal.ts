// "Signal, not noise" (T-093): at world zoom the verdict layer draws ABOVE and BELOW normal at full strength and the
// three quiet verdicts (within normal, cannot determine, no detected activity) nearly transparent, so the Earth shows
// and the departures from normal stand out. Display only: the stored verdicts, the tooltip, the cell card and the
// answer panel are unchanged, and a quiet cell can still be hovered and clicked.
import type { MapLayer, Verdict } from '../../api/contract.ts'
import type { Rgba } from './scale.ts'

/** The verdicts drawn quietly when zoomed out. */
export const QUIET_VERDICTS: readonly Verdict[] = ['WITHIN_NORMAL', 'CANNOT_DETERMINE', 'NO_DETECTED_ACTIVITY']
/** Share of their own alpha the quiet verdicts keep at zoom 3 and below (the Lead's default, plan section 15.3). */
export const QUIET_ALPHA = 0.12
/** At this zoom and below the quiet verdicts are at QUIET_ALPHA. */
export const QUIET_MAX_ZOOM = 3
/** From this zoom every verdict is at full strength; between the two the quiet ones fade up linearly. */
export const FULL_FROM_ZOOM = 4
/** The fade is followed in steps of this many zoom levels: smooth to the eye, and few colour updates. */
export const FADE_STEP = 0.05

export function isQuietVerdict(verdict: Verdict): boolean {
  return QUIET_VERDICTS.includes(verdict)
}

/**
 * The share of their alpha the quiet verdicts keep at a zoom: QUIET_ALPHA up to zoom 3, full (1) from zoom 4, linear
 * in between. "Show all verdicts" keeps every verdict at full strength at every zoom.
 */
export function quietAlpha(zoom: number, showAll: boolean): number {
  if (showAll || !Number.isFinite(zoom) || zoom >= FULL_FROM_ZOOM) return 1
  if (zoom <= QUIET_MAX_ZOOM) return QUIET_ALPHA
  const t = (zoom - QUIET_MAX_ZOOM) / (FULL_FROM_ZOOM - QUIET_MAX_ZOOM)
  return QUIET_ALPHA + (1 - QUIET_ALPHA) * t
}

/**
 * The zoom the map keeps for the fade: limited to the fade band (3 to 4) and rounded to FADE_STEP, so the map's state
 * changes only while the zoom crosses a step inside the band, not on every frame of a zoom.
 */
export function fadeZoom(zoom: number): number {
  if (!Number.isFinite(zoom)) return FULL_FROM_ZOOM
  const clamped = Math.min(Math.max(zoom, QUIET_MAX_ZOOM), FULL_FROM_ZOOM)
  return Math.round(clamped / FADE_STEP) * FADE_STEP
}

/**
 * A colour with the rule applied: on the verdict layer a quiet verdict keeps `factor` of its alpha (rounded to a whole
 * 0 to 255 value); ABOVE and BELOW, and every colour of the activity layers, are returned unchanged. Used for the fill
 * and for the thin cell stroke, so the grid does not come back as noise.
 */
export function signalFill(fill: Rgba, verdict: Verdict, layer: MapLayer, factor: number): Rgba {
  if (layer !== 'verdict' || factor >= 1 || !isQuietVerdict(verdict)) return fill
  const f = Math.min(Math.max(factor, 0), 1)
  return [fill[0], fill[1], fill[2], Math.round(fill[3] * f)]
}
