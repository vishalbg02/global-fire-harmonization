import { describe, expect, it } from 'vitest'
import { VERDICTS } from '../../api/contract.ts'
import type { Verdict } from '../../api/contract.ts'
import { FULL_FROM_ZOOM, QUIET_ALPHA, QUIET_MAX_ZOOM, QUIET_VERDICTS, fadeZoom, isQuietVerdict, quietAlpha, signalFill } from './signal.ts'
import type { Rgba } from './scale.ts'

describe('signal, not noise: the quiet share at a zoom (T-093)', () => {
  it('uses the approved defaults: 12% at zoom 3 and below, full from zoom 4', () => {
    expect(QUIET_ALPHA).toBe(0.12)
    expect(QUIET_MAX_ZOOM).toBe(3)
    expect(FULL_FROM_ZOOM).toBe(4)
  })

  it('is 12% at world zoom and up to zoom 3', () => {
    for (const z of [0, 1.2, 2, 2.99, 3]) expect(quietAlpha(z, false)).toBe(0.12)
  })

  it('fades up linearly between zoom 3 and 4', () => {
    expect(quietAlpha(3.5, false)).toBeCloseTo(0.56, 10)
    expect(quietAlpha(3.25, false)).toBeCloseTo(0.12 + 0.88 * 0.25, 10)
    const steps = [3, 3.2, 3.4, 3.6, 3.8, 4].map((z) => quietAlpha(z, false))
    for (let i = 1; i < steps.length; i++) expect(steps[i]).toBeGreaterThan(steps[i - 1])
  })

  it('is full from zoom 4, and at every zoom with "Show all verdicts"', () => {
    for (const z of [4, 4.01, 6, 12]) expect(quietAlpha(z, false)).toBe(1)
    for (const z of [0, 1.2, 3, 3.5, 4, 9]) expect(quietAlpha(z, true)).toBe(1)
  })

  it('draws everything at full strength for a zoom that is not a number', () => {
    expect(quietAlpha(Number.NaN, false)).toBe(1)
    expect(fadeZoom(Number.NaN)).toBe(4)
  })
})

describe('the zoom kept for the fade', () => {
  it('is limited to the band 3 to 4, so zooming outside it changes nothing', () => {
    expect(fadeZoom(0.8)).toBe(3)
    expect(fadeZoom(2.7)).toBe(3)
    expect(fadeZoom(4.2)).toBe(4)
    expect(fadeZoom(11)).toBe(4)
  })

  it('moves in steps of 0.05 inside the band', () => {
    expect(fadeZoom(3.51)).toBeCloseTo(3.5, 10)
    expect(fadeZoom(3.53)).toBeCloseTo(3.55, 10)
    expect(new Set(Array.from({ length: 1001 }, (_, i) => fadeZoom(3 + i / 1000))).size).toBe(21)
  })

  it('gives the same strength as the exact zoom, to within half a step', () => {
    for (let z = 3; z <= 4; z += 0.013) {
      expect(Math.abs(quietAlpha(fadeZoom(z), false) - quietAlpha(z, false))).toBeLessThanOrEqual(0.88 * 0.025 + 1e-9)
    }
  })
})

describe('the colour with the rule applied', () => {
  const fill: Rgba = [153, 153, 153, 200]

  it('quiets exactly within normal, cannot determine and no detected activity', () => {
    expect([...QUIET_VERDICTS].sort()).toEqual(['CANNOT_DETERMINE', 'NO_DETECTED_ACTIVITY', 'WITHIN_NORMAL'])
    expect(VERDICTS.filter((v) => !isQuietVerdict(v))).toEqual(['ABOVE_NORMAL', 'BELOW_NORMAL'])
  })

  it("keeps 12% of a quiet verdict's alpha and its colour", () => {
    for (const v of QUIET_VERDICTS) expect(signalFill(fill, v, 'verdict', 0.12)).toEqual([153, 153, 153, 24])
  })

  it('leaves above and below normal, and the activity layers, unchanged', () => {
    for (const v of ['ABOVE_NORMAL', 'BELOW_NORMAL'] as Verdict[]) expect(signalFill(fill, v, 'verdict', 0.12)).toBe(fill)
    for (const layer of ['raw', 'harmonized'] as const) {
      for (const v of VERDICTS) expect(signalFill(fill, v, layer, 0.12)).toBe(fill)
    }
  })

  it('changes nothing at full strength, and keeps a quiet cell drawn (never alpha 0) at the quietest', () => {
    for (const v of VERDICTS) expect(signalFill(fill, v, 'verdict', 1)).toBe(fill)
    expect(signalFill([200, 200, 200, 199], 'WITHIN_NORMAL', 'verdict', QUIET_ALPHA)[3]).toBeGreaterThan(0)
  })
})
