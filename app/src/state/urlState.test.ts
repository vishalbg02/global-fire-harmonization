import { describe, expect, it } from 'vitest'
import { customArea } from './bbox.ts'
import { WORLD, initialSelection } from './selection.ts'
import type { Selection } from './selection.ts'
import { encodeSelection, selectionFromUrl } from './urlState.ts'

const linked = (s: Selection) => ({ area: s.area, month: s.month, source: s.source, mapMode: s.mapMode, valueMode: s.valueMode })

describe('encodeSelection', () => {
  it('leaves the defaults out: an empty selection is an empty query', () => {
    expect(encodeSelection(linked(initialSelection))).toBe('')
  })

  it('encodes the area, the month and the display modes', () => {
    const query = encodeSelection({
      area: { entity_type: 'COUNTRY', entity_id: 'IDN', entity_name: 'Indonesia' },
      month: { year: 2015, month: 9 },
      source: 'raw',
      mapMode: 'activity',
      valueMode: 'activity',
    })
    const params = new URLSearchParams(query)
    expect(params.get('area')).toBe('COUNTRY:IDN')
    expect(params.get('month')).toBe('2015-09')
    expect(params.get('source')).toBe('raw')
    expect(params.get('map')).toBe('activity')
    expect(params.get('value')).toBe('activity')
  })

  it('encodes a custom area by its box', () => {
    const query = encodeSelection({ ...linked(initialSelection), area: customArea([100, 0, 101.5, 1]) })
    expect(new URLSearchParams(query).get('area')).toBe('CUSTOM:100,0,101.5,1')
  })
})

describe('selectionFromUrl', () => {
  it('returns the initial selection for an empty or irrelevant query', () => {
    expect(selectionFromUrl('')).toEqual(initialSelection)
    expect(selectionFromUrl('?utm_source=x&foo=bar')).toEqual(initialSelection)
  })

  const roundTrips: [string, Selection][] = [
    ['the world, no month', initialSelection],
    [
      'a country in a month, raw activity',
      {
        ...initialSelection,
        area: { entity_type: 'COUNTRY', entity_id: 'IDN', entity_name: 'IDN' },
        entity: { entity_type: 'COUNTRY', entity_id: 'IDN', entity_name: 'IDN' },
        month: { year: 2015, month: 9 },
        source: 'raw',
        mapMode: 'activity',
        valueMode: 'activity',
      },
    ],
    [
      'a continent, harmonized activity',
      {
        ...initialSelection,
        area: { entity_type: 'CONTINENT', entity_id: 'AS', entity_name: 'AS' },
        entity: { entity_type: 'CONTINENT', entity_id: 'AS', entity_name: 'AS' },
        month: { year: 2002, month: 7 },
        mapMode: 'activity',
        valueMode: 'activity',
      },
    ],
    [
      'a custom box',
      {
        ...initialSelection,
        area: customArea([-10.5, 35, 4, 44]),
        entity: customArea([-10.5, 35, 4, 44]),
        month: { year: 2026, month: 11 },
      },
    ],
  ]

  for (const [name, selection] of roundTrips) {
    it(`round-trips ${name}: state to URL to state is unchanged`, () => {
      const restored = selectionFromUrl(encodeSelection(linked(selection)))
      expect(restored).toEqual({ ...selection, fit: null })
      expect(encodeSelection(linked(restored))).toBe(encodeSelection(linked(selection)))
    })
  }

  it('ignores unknown and malformed values instead of failing', () => {
    const restored = selectionFromUrl(
      'area=PLANET:EARTH&month=2020-13&source=sideways&map=3d&value=banana',
    )
    expect(restored).toEqual(initialSelection)
  })

  it('ignores malformed areas of each kind', () => {
    for (const area of ['COUNTRY:idn', 'COUNTRY:', 'COUNTRY:TOOLONG', 'CONTINENT:ASIA', 'CUSTOM:1,2,3', 'CUSTOM:a,b,c,d', 'CUSTOM:10,0,0,5', 'CUSTOM:0,0,200,5', 'GLOBAL:x', '']) {
      expect(selectionFromUrl(`area=${encodeURIComponent(area)}`).area).toEqual(WORLD)
    }
  })

  it('ignores an invalid month and keeps the rest', () => {
    const restored = selectionFromUrl('area=COUNTRY:BRA&month=2020-00')
    expect(restored.month).toBeNull()
    expect(restored.area.entity_id).toBe('BRA')
  })

  it('never produces raw together with % of normal, or raw with the verdict map', () => {
    expect(selectionFromUrl('source=raw&value=pct&map=activity').source).toBe('harmonized')
    expect(selectionFromUrl('source=raw&value=activity&map=verdict').source).toBe('harmonized')
    expect(selectionFromUrl('source=raw&value=activity&map=activity').source).toBe('raw')
  })

  it('puts the selected country on the map selection, and nothing for the world', () => {
    expect(selectionFromUrl('area=COUNTRY:BRA').entity?.entity_id).toBe('BRA')
    expect(selectionFromUrl('area=GLOBAL').entity).toBeNull()
  })
})
