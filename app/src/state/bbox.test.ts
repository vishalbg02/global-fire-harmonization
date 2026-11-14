import { describe, expect, it } from 'vitest'
import { bboxFromRing, bboxLabel, checkBbox, customArea, customId, parseBboxFields } from './bbox.ts'

describe('checkBbox', () => {
  it('accepts a valid box and returns it unchanged', () => {
    expect(checkBbox(100, 0, 101, 1)).toEqual({ ok: true, bbox: [100, 0, 101, 1] })
    expect(checkBbox(-180, -90, 180, 90)).toEqual({ ok: true, bbox: [-180, -90, 180, 90] })
  })

  it('rejects west not less than east, and says boxes that cross the antimeridian are not supported', () => {
    const crossing = checkBbox(170, 0, -170, 10)
    expect(crossing.ok).toBe(false)
    if (!crossing.ok) {
      expect(crossing.message).toContain('West must be less than east')
      expect(crossing.message).toContain('antimeridian')
    }
    const same = checkBbox(10, 0, 10, 5)
    expect(same.ok).toBe(false)
    if (!same.ok) expect(same.message).toBe('West must be less than east.')
  })

  it('rejects south not less than north', () => {
    for (const [s, n] of [[10, 10], [20, 10]]) {
      const check = checkBbox(0, s, 10, n)
      expect(check.ok).toBe(false)
      if (!check.ok) expect(check.message).toBe('South must be less than north.')
    }
  })

  it('rejects values outside the longitude and latitude ranges, naming the field', () => {
    const cases: [number[], string][] = [
      [[-181, 0, 10, 1], 'West must be between -180 and 180.'],
      [[0, 0, 181, 1], 'East must be between -180 and 180.'],
      [[0, -91, 10, 1], 'South must be between -90 and 90.'],
      [[0, 0, 10, 91], 'North must be between -90 and 90.'],
    ]
    for (const [[w, s, e, n], message] of cases) {
      const check = checkBbox(w, s, e, n)
      expect(check.ok).toBe(false)
      if (!check.ok) expect(check.message).toBe(message)
    }
  })

  it('rejects a value that is not a number', () => {
    const check = checkBbox(Number.NaN, 0, 10, 1)
    expect(check.ok).toBe(false)
    if (!check.ok) expect(check.message).toBe('Enter a number for west.')
    expect(checkBbox(0, 0, Number.POSITIVE_INFINITY, 1).ok).toBe(false)
  })
})

describe('parseBboxFields', () => {
  it('parses typed text, including decimals and spaces', () => {
    expect(parseBboxFields({ west: ' 100.5 ', south: '-1.25', east: '101', north: '0' })).toEqual({
      ok: true,
      bbox: [100.5, -1.25, 101, 0],
    })
  })

  it('treats an empty field as missing, and text as not a number', () => {
    const empty = parseBboxFields({ west: '', south: '0', east: '1', north: '1' })
    expect(empty.ok).toBe(false)
    if (!empty.ok) expect(empty.message).toBe('Enter a number for west.')
    const text = parseBboxFields({ west: '0', south: 'abc', east: '1', north: '1' })
    expect(text.ok).toBe(false)
    if (!text.ok) expect(text.message).toBe('Enter a number for south.')
  })
})

describe('custom area naming', () => {
  it('builds the id from the box rounded to 2 decimals', () => {
    expect(customId([100, 0, 101.456, 1])).toBe('custom_w100.00_s0.00_e101.46_n1.00')
  })

  it('makes a custom area with the box and a plain name', () => {
    const area = customArea([100, 0, 101, 1])
    expect(area).toEqual({
      entity_type: 'CUSTOM',
      entity_id: 'custom_w100.00_s0.00_e101.00_n1.00',
      entity_name: 'Custom area',
      bbox: [100, 0, 101, 1],
    })
  })

  it('labels a box for people', () => {
    expect(bboxLabel([100, 0, 101, 1])).toBe('W 100.00, S 0.00, E 101.00, N 1.00')
  })
})

describe('bboxFromRing (a drawn rectangle)', () => {
  const ring = [
    [71.66966588, -4.250239021],
    [125.534981984, -4.250239021],
    [125.534981984, 25.744466955],
    [71.66966588, 25.744466955],
    [71.66966588, -4.250239021],
  ]

  it('takes the smallest box around the points and rounds it to 2 decimals', () => {
    expect(bboxFromRing(ring)).toEqual({ ok: true, bbox: [71.67, -4.25, 125.53, 25.74] })
  })

  it('does not depend on which corner comes first', () => {
    expect(bboxFromRing([...ring].reverse())).toEqual(bboxFromRing(ring))
  })

  it('clamps a rectangle that runs past the edges of the map to valid degrees', () => {
    const wide = [[-190, -95], [190, -95], [190, 95], [-190, 95]]
    expect(bboxFromRing(wide)).toEqual({ ok: true, bbox: [-180, -90, 180, 90] })
  })

  it('rejects a rectangle with no area once rounded, and an empty ring', () => {
    expect(bboxFromRing([[10.001, 5.001], [10.002, 5.002]]).ok).toBe(false)
    const none = bboxFromRing([])
    expect(none.ok).toBe(false)
  })
})
