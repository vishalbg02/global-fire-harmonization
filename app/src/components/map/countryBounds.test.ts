import { describe, expect, it } from 'vitest'
import { polygonBounds } from './countryBounds.ts'

// SYNTHETIC shapes, not real country boundaries.
const square = (w: number, s: number, e: number, n: number) => [[[w, s], [e, s], [e, n], [w, n], [w, s]]]

describe('polygonBounds (SYNTHETIC polygons)', () => {
  it('is the box of a polygon', () => {
    const f = { type: 'Feature', geometry: { type: 'Polygon', coordinates: square(68, 8, 97, 37.05) } }
    expect(polygonBounds(f)).toEqual([68, 8, 97, 37.05])
  })

  it('covers every part of a multi-polygon, holes included', () => {
    const f = {
      geometry: {
        type: 'MultiPolygon',
        coordinates: [square(10, 0, 12, 2), [...square(20, 5, 30, 9), [[21, 6], [22, 6], [22, 7], [21, 6]]]],
      },
    }
    expect(polygonBounds(f)).toEqual([10, 0, 30, 9])
  })

  it('a shape split at 180 degrees spans -180 to 180, like the cell bounds (no wrapping)', () => {
    const f = { geometry: { type: 'MultiPolygon', coordinates: [square(170, -20, 180, -15), square(-180, -19, -178, -16)] } }
    expect(polygonBounds(f)).toEqual([-180, -20, 180, -15])
  })

  it('is null for a missing or unusable shape, so the caller falls back to the cell bounds', () => {
    expect(polygonBounds(null)).toBeNull()
    expect(polygonBounds(undefined)).toBeNull()
    expect(polygonBounds({})).toBeNull()
    expect(polygonBounds({ geometry: null })).toBeNull()
    expect(polygonBounds({ geometry: { type: 'Point', coordinates: [1, 2] } })).toBeNull()
    expect(polygonBounds({ geometry: { type: 'Polygon', coordinates: [] } })).toBeNull()
    expect(polygonBounds({ geometry: { type: 'Polygon', coordinates: [[[1, 1], [1, 1]]] } })).toBeNull()
  })
})
