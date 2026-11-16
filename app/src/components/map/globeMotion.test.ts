import { describe, expect, it } from 'vitest'
import {
  FLY_MS,
  IDLE_MS,
  MAX_FRAME_MS,
  ROTATION_MAX_ZOOM,
  ROTATION_PAUSED_KEY,
  SECONDS_PER_TURN,
  WORLD_GLOBE_FILL,
  fitPadding,
  flyEasing,
  flyOptions,
  globeScreenRadius,
  globeWorldZoom,
  idleLongEnough,
  nextLongitude,
  readRotationPaused,
  rotationAllowed,
  rotationMaxZoom,
  wrapLongitude,
  writeRotationPaused,
} from './globeMotion.ts'
import type { RotationConditions } from './globeMotion.ts'

describe('fly-to (T-093)', () => {
  it('lasts about 1.2 s with an ease-out curve', () => {
    expect(FLY_MS).toBe(1200)
    expect(flyEasing(0)).toBe(0)
    expect(flyEasing(1)).toBe(1)
    expect(flyEasing(0.5)).toBeGreaterThan(0.5)
    for (let t = 0.05; t <= 1; t += 0.05) expect(flyEasing(t)).toBeGreaterThan(flyEasing(t - 0.05))
    expect(flyEasing(-1)).toBe(0)
    expect(flyEasing(2)).toBe(1)
  })

  it('is instant under reduced motion', () => {
    expect(flyOptions(false)).toMatchObject({ animate: true, duration: 1200 })
    expect(flyOptions(true)).toMatchObject({ animate: false, duration: 0 })
  })
})

describe('idle rotation: when the globe may turn', () => {
  const ok: RotationConditions = { shape: 'globe', zoom: 1.8, worldZoom: 2.1, reducedMotion: false, paused: false, drawing: false, pinned: false, hidden: false }

  it('turns on the globe at the world view when nothing stops it', () => {
    expect(rotationAllowed(ok)).toBe(true)
  })

  it('never on the flat map, zoomed in, under reduced motion, paused, while drawing, with a pinned card or a hidden tab', () => {
    expect(rotationAllowed({ ...ok, shape: 'flat' })).toBe(false)
    expect(rotationAllowed({ ...ok, zoom: ROTATION_MAX_ZOOM })).toBe(false)
    expect(rotationAllowed({ ...ok, zoom: 6 })).toBe(false)
    expect(rotationAllowed({ ...ok, zoom: Number.NaN })).toBe(false)
    expect(rotationAllowed({ ...ok, reducedMotion: true })).toBe(false)
    expect(rotationAllowed({ ...ok, paused: true })).toBe(false)
    expect(rotationAllowed({ ...ok, drawing: true })).toBe(false)
    expect(rotationAllowed({ ...ok, pinned: true })).toBe(false)
    expect(rotationAllowed({ ...ok, hidden: true })).toBe(false)
  })

  it('counts the world view of a big screen as the world view too', () => {
    expect(rotationMaxZoom(1.9)).toBe(2.5)
    expect(rotationMaxZoom(3.0)).toBeCloseTo(3.4, 10)
    expect(rotationMaxZoom(Number.NaN)).toBe(2.5)
    expect(rotationAllowed({ ...ok, zoom: 3.0, worldZoom: 3.0 })).toBe(true)
  })

  it('starts only after 8 s without interaction', () => {
    expect(IDLE_MS).toBe(8000)
    expect(idleLongEnough(10_000, 2_001)).toBe(false)
    expect(idleLongEnough(10_000, 2_000)).toBe(true)
  })
})

describe('idle rotation: how fast and which way', () => {
  it('turns once in 3 to 4 minutes', () => {
    expect(SECONDS_PER_TURN).toBeGreaterThanOrEqual(180)
    expect(SECONDS_PER_TURN).toBeLessThanOrEqual(240)
    let lng = 0
    for (let i = 0; i < 10; i++) lng = nextLongitude(lng, 100)
    expect(lng).toBeCloseTo(-360 / SECONDS_PER_TURN, 10)
  })

  it('turns eastward: the centre longitude decreases, so the surface moves left to right', () => {
    expect(nextLongitude(20, 16)).toBeLessThan(20)
  })

  it('never jumps after a long gap (a hidden or busy tab) and never goes back', () => {
    expect(nextLongitude(0, 60_000)).toBeCloseTo(nextLongitude(0, MAX_FRAME_MS), 10)
    expect(nextLongitude(5, -50)).toBe(5)
  })

  it('wraps the longitude across the date line', () => {
    expect(wrapLongitude(190)).toBe(-170)
    expect(wrapLongitude(-190)).toBe(170)
    expect(wrapLongitude(540)).toBe(180)
    expect(wrapLongitude(45)).toBe(45)
    const near = nextLongitude(-179.99, MAX_FRAME_MS)
    expect(near).toBeGreaterThan(179)
    expect(near).toBeLessThanOrEqual(180)
  })
})

describe('the world view on the globe', () => {
  it("fills WORLD_GLOBE_FILL of the stage's shorter side, through MapLibre's perspective", () => {
    for (const [w, h] of [[1060, 747], [900, 567], [375, 420]]) {
      const z = globeWorldZoom(w, h)
      expect((2 * globeScreenRadius(z, h)) / Math.min(w, h)).toBeCloseTo(WORLD_GLOBE_FILL, 6)
    }
  })

  it('matches the outline measured in the browser (1060 x 747 stage, zoom 1.875: radius about 242 px)', () => {
    expect(globeScreenRadius(1.8745, 747)).toBeGreaterThan(236)
    expect(globeScreenRadius(1.8745, 747)).toBeLessThan(250)
  })

  it('stays within zoom 0 to 4 and handles an empty stage', () => {
    expect(globeWorldZoom(50, 50)).toBe(0)
    expect(globeWorldZoom(40_000, 40_000)).toBe(4)
    expect(globeWorldZoom(0, 600)).toBe(1)
  })
})

describe('padding for a fit', () => {
  it('keeps the floating panels clear on a large map', () => {
    expect(fitPadding(1060, 740, { top: 0, right: 40, bottom: 48, left: 310 })).toEqual({ top: 24, right: 64, bottom: 72, left: 334 })
  })

  it('shrinks so that at least a third of a small map stays free', () => {
    const p = fitPadding(360, 300, { top: 120, right: 40, bottom: 48, left: 310 })
    expect(p.left + p.right).toBeLessThanOrEqual(240)
    expect(p.top + p.bottom).toBeLessThanOrEqual(200)
    expect(p.left).toBeGreaterThan(p.right)
  })
})

describe('the remembered "Pause rotation" choice', () => {
  const memory = () => {
    const data = new Map<string, string>()
    return { getItem: (k: string) => data.get(k) ?? null, setItem: (k: string, v: string) => void data.set(k, v), data }
  }

  it('is read back after it is written', () => {
    const s = memory()
    expect(readRotationPaused(s)).toBe(false)
    writeRotationPaused(s, true)
    expect(s.data.get(ROTATION_PAUSED_KEY)).toBe('1')
    expect(readRotationPaused(s)).toBe(true)
    writeRotationPaused(s, false)
    expect(readRotationPaused(s)).toBe(false)
  })

  it('never throws when storage is missing or blocked', () => {
    const blocked = {
      getItem: () => {
        throw new Error('blocked')
      },
      setItem: () => {
        throw new Error('blocked')
      },
    }
    expect(readRotationPaused(blocked)).toBe(false)
    expect(() => writeRotationPaused(blocked, true)).not.toThrow()
    expect(readRotationPaused(null)).toBe(false)
    expect(() => writeRotationPaused(undefined, true)).not.toThrow()
  })
})
