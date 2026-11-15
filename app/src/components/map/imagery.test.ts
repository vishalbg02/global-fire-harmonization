import { describe, expect, it } from 'vitest'
import { BASEMAP_LAYER, BASEMAP_SOURCE, TileCounter, buildStyle, layerKeyOfSource } from './imagery.ts'

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
