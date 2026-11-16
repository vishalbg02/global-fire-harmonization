// Motion of the Earth (T-093): the fly-to on a selection, the world view on the globe, and the slow idle rotation.
// Pure timing and geometry only; MapView.tsx wires it to the map. Every motion is off under prefers-reduced-motion.

/** Length of the fly-to on a selection, in ms (instant under reduced motion). */
export const FLY_MS = 1200
/** No interaction for this long (ms) before the globe starts turning. */
export const IDLE_MS = 8000
/** One full turn of the idle rotation takes this many seconds (3.5 minutes): slow enough to read the map. */
export const SECONDS_PER_TURN = 210
/** The idle rotation runs only at the world view: below this zoom (or a little above the world view on a big screen). */
export const ROTATION_MAX_ZOOM = 2.5
/** A longer gap between two frames (a busy or throttled tab) moves the globe by this much at most, never by a jump. */
export const MAX_FRAME_MS = 100
/** Where the user's "Pause rotation" choice is kept in localStorage. */
export const ROTATION_PAUSED_KEY = 'fire-harmonization:globe-rotation-paused'
/** The centre of the world view on the globe (the longitude is kept when flying back from an area). */
export const WORLD_CENTER: readonly [number, number] = [10, 15]
/** Share of the stage's shorter side the globe fills at the world view. */
export const WORLD_GLOBE_FILL = 0.78
/** MapLibre's camera: the distance to the map centre is 1.5 times the map height (field of view 36.87 degrees). */
const CAMERA_DISTANCE_PER_HEIGHT = 1.5

/** Ease-out (cubic): fast start, gentle arrival. */
export function flyEasing(t: number): number {
  const c = Math.min(Math.max(t, 0), 1)
  return 1 - (1 - c) ** 3
}

/** Fly-to options for MapLibre: about 1.2 s with ease-out, or no animation under reduced motion. */
export function flyOptions(reducedMotion: boolean): { animate: boolean; duration: number; easing: (t: number) => number } {
  return { animate: !reducedMotion, duration: reducedMotion ? 0 : FLY_MS, easing: flyEasing }
}

export interface RotationConditions {
  shape: 'flat' | 'globe'
  zoom: number
  /** The zoom of the world view on this screen (globeWorldZoom). */
  worldZoom: number
  reducedMotion: boolean
  /** The user paused it with the map's button. */
  paused: boolean
  /** A rectangle or polygon is being drawn. */
  drawing: boolean
  /** A cell card is pinned on the map. */
  pinned: boolean
  /** The browser tab is hidden. */
  hidden: boolean
}

/** The zoom below which the globe may turn: about the world view (2.5, or a little above the world view of a big screen). */
export function rotationMaxZoom(worldZoom: number): number {
  return Math.max(ROTATION_MAX_ZOOM, Number.isFinite(worldZoom) ? worldZoom + 0.4 : ROTATION_MAX_ZOOM)
}

/** Whether the globe may turn at all now (the idle time is checked separately). */
export function rotationAllowed(c: RotationConditions): boolean {
  return (
    c.shape === 'globe' &&
    Number.isFinite(c.zoom) &&
    c.zoom < rotationMaxZoom(c.worldZoom) &&
    !c.reducedMotion &&
    !c.paused &&
    !c.drawing &&
    !c.pinned &&
    !c.hidden
  )
}

/** True once there has been no interaction for IDLE_MS. */
export function idleLongEnough(now: number, lastInteraction: number): boolean {
  return now - lastInteraction >= IDLE_MS
}

/** A longitude brought into -180 to 180. */
export function wrapLongitude(lng: number): number {
  const w = ((((lng + 180) % 360) + 360) % 360) - 180
  return w === -180 && lng > 0 ? 180 : w
}

/**
 * The map centre's longitude after `dtMs` of rotation. The Earth turns eastward: the surface moves from left to right
 * on the screen, so the centre's longitude decreases. A long gap counts as MAX_FRAME_MS, so the globe never jumps.
 */
export function nextLongitude(lng: number, dtMs: number): number {
  const dt = Math.min(Math.max(dtMs, 0), MAX_FRAME_MS)
  return wrapLongitude(lng - (360 / SECONDS_PER_TURN) * (dt / 1000))
}

/**
 * The zoom at which the globe's outline fills WORLD_GLOBE_FILL of the stage's shorter side, seen through MapLibre's
 * perspective camera. For a globe of radius R pixels at a camera distance f (1.5 times the height) above the surface,
 * the outline's radius on screen is r = R f / sqrt(f^2 + 2 f R); solved for R, then MapLibre's world size at the
 * centre latitude (2 pi R cos(lat)) gives the zoom (world size 512 px at zoom 0).
 */
export function globeWorldZoom(widthPx: number, heightPx: number, lat = WORLD_CENTER[1]): number {
  const side = Math.min(widthPx, heightPx)
  if (!(side > 0) || !(heightPx > 0)) return 1
  const r = (WORLD_GLOBE_FILL * side) / 2
  const f = CAMERA_DISTANCE_PER_HEIGHT * heightPx
  const radius = (r * r + r * Math.sqrt(r * r + f * f)) / f
  const z = Math.log2((2 * Math.PI * radius * Math.cos((lat * Math.PI) / 180)) / 512)
  return Math.min(Math.max(z, 0), 4)
}

/** The on-screen radius of the globe's outline at a zoom (the inverse of globeWorldZoom, for its test). */
export function globeScreenRadius(zoom: number, heightPx: number, lat = WORLD_CENTER[1]): number {
  const radius = (512 * 2 ** zoom) / (2 * Math.PI * Math.cos((lat * Math.PI) / 180))
  const f = CAMERA_DISTANCE_PER_HEIGHT * heightPx
  return (radius * f) / Math.sqrt(f * f + 2 * f * radius)
}

export interface Padding {
  top: number
  right: number
  bottom: number
  left: number
}

/**
 * Padding for fitting an area: the space the floating panels take on each side, plus a margin. It is scaled down when
 * it would leave less than a third of the map free (a small map, a phone), so a fit always has room.
 */
export function fitPadding(widthPx: number, heightPx: number, reserved: Padding, margin = 24): Padding {
  const p = { top: reserved.top + margin, right: reserved.right + margin, bottom: reserved.bottom + margin, left: reserved.left + margin }
  const maxX = (widthPx * 2) / 3
  const maxY = (heightPx * 2) / 3
  const scaleX = p.left + p.right > maxX ? maxX / (p.left + p.right) : 1
  const scaleY = p.top + p.bottom > maxY ? maxY / (p.top + p.bottom) : 1
  const round = (v: number) => Math.max(0, Math.floor(v))
  return { top: round(p.top * scaleY), bottom: round(p.bottom * scaleY), left: round(p.left * scaleX), right: round(p.right * scaleX) }
}

type StorageLike = Pick<Storage, 'getItem' | 'setItem'>

/** The remembered "Pause rotation" choice; false when nothing is stored or storage is blocked. */
export function readRotationPaused(storage: StorageLike | null | undefined): boolean {
  try {
    return storage?.getItem(ROTATION_PAUSED_KEY) === '1'
  } catch {
    return false
  }
}

/** Remembers the choice; a blocked or full storage is ignored (the choice then lasts for the visit). */
export function writeRotationPaused(storage: StorageLike | null | undefined, paused: boolean): void {
  try {
    storage?.setItem(ROTATION_PAUSED_KEY, paused ? '1' : '0')
  } catch {
    // Private mode or blocked storage: nothing to do.
  }
}
