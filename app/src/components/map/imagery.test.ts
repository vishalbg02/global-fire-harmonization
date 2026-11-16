import { describe, expect, it } from 'vitest'
import { BASEMAP_LAYER, BASEMAP_SOURCE, SPACE_COLOR, TileCounter, buildStyle, layerKeyOfSource } from './imagery.ts'

describe('map style', () => {
  it('has the Blue Marble raster above the plain background', () => {
    const s = buildStyle(true)
    expect(Object.keys(s.sources)).toEqual([BASEMAP_SOURCE])
    expect(s.layers.map((l) => l.id)).toEqual(['background', BASEMAP_LAYER])
  })
  it('asks GIBS for nothing in the offline copy', () => {
    const s = buildStyle(false)
    expect(s.sources).toEqual({})
    expect(s.layers.map((l) => l.id)).toEqual(['background'])
  })
  it('puts the globe in dark space with a subtle atmosphere that fades out when zoomed in (T-093)', () => {
    for (const withImagery of [true, false]) {
      const sky = buildStyle(withImagery).sky
      expect(sky?.['sky-color']).toBe(SPACE_COLOR)
      expect(sky?.['horizon-color']).toBe(SPACE_COLOR)
      const blend = sky?.['atmosphere-blend'] as unknown[]
      // ['interpolate', ['linear'], ['zoom'], z0, v0, z1, v1, ...]: at most 0.6 (MapLibre's default is 0.8), 0 zoomed in.
      const values = blend.slice(3).filter((_, i) => i % 2 === 1) as number[]
      expect(Math.max(...values)).toBeLessThanOrEqual(0.6)
      expect(values[values.length - 1]).toBe(0)
    }
  })
})

describe('tile counter', () => {
  it('reports failure only after repeated errors with few loaded tiles', () => {
    const t = new TileCounter()
    expect(t.fail('basemap')).toBe(false)
    expect(t.fail('basemap')).toBe(false)
    expect(t.fail('basemap')).toBe(true)
    t.reset('basemap')
    t.ok('basemap')
    t.ok('basemap')
    t.ok('basemap')
    expect(t.fail('basemap')).toBe(false)
  })
  it('maps source ids to layers', () => {
    expect(layerKeyOfSource(BASEMAP_SOURCE)).toBe('basemap')
    expect(layerKeyOfSource('countries')).toBeNull()
  })
})
