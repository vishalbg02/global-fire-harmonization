import { describe, expect, it } from 'vitest'
import { monthKey, monthRange } from './months.ts'
import { WORLD, initialSelection, selectionReducer } from './selection.ts'

describe('monthRange', () => {
  it('spans first to latest inclusive and marks provisional months', () => {
    const months = monthRange('2025-11', '2026-02', ['2026-02'])
    expect(months.map((m) => monthKey(m.year, m.month))).toEqual(['2025-11', '2025-12', '2026-01', '2026-02'])
    expect(months.map((m) => m.provisional)).toEqual([false, false, false, true])
  })

  it('covers the whole record from 2002-07', () => {
    const months = monthRange('2002-07', '2026-10', [])
    expect(months[0]).toEqual({ year: 2002, month: 7, provisional: false })
    expect(months).toHaveLength(12 * 24 + 4)
  })

  it('returns a single month when first equals latest', () => {
    expect(monthRange('2020-05', '2020-05', [])).toHaveLength(1)
  })
})

describe('selectionReducer', () => {
  it('starts with no entity, the world as the calendar area, no month, the verdict layer and % of normal', () => {
    expect(initialSelection).toEqual({
      entity: null,
      area: WORLD,
      month: null,
      layer: 'verdict',
      valueMode: 'pct',
    })
  })

  it('sets and clears the selected entity', () => {
    const entity = { entity_type: 'COUNTRY' as const, entity_id: 'NOR', entity_name: 'Norway' }
    const selected = selectionReducer(initialSelection, { type: 'select-entity', entity })
    expect(selected.entity).toEqual(entity)
    expect(selectionReducer(selected, { type: 'clear-entity' }).entity).toBeNull()
  })

  it('sets the month and the layer without touching the rest', () => {
    const s1 = selectionReducer(initialSelection, { type: 'set-month', year: 2015, month: 9 })
    const s2 = selectionReducer(s1, { type: 'set-layer', layer: 'raw' })
    expect(s2).toEqual({
      entity: null,
      area: WORLD,
      month: { year: 2015, month: 9 },
      layer: 'raw',
      valueMode: 'pct',
    })
  })

  it('shows the selected country, continent or world in the calendar', () => {
    const country = selectionReducer(initialSelection, {
      type: 'select-entity',
      entity: { entity_type: 'COUNTRY', entity_id: 'IDN', entity_name: 'Indonesia' },
    })
    expect(country.area).toEqual({ entity_type: 'COUNTRY', entity_id: 'IDN', entity_name: 'Indonesia' })
    const continent = selectionReducer(country, {
      type: 'select-entity',
      entity: { entity_type: 'CONTINENT', entity_id: 'AS', entity_name: 'Asia' },
    })
    expect(continent.area.entity_type).toBe('CONTINENT')
  })

  it('keeps the calendar area when a cell is selected (cells have no series)', () => {
    const country = selectionReducer(initialSelection, {
      type: 'select-entity',
      entity: { entity_type: 'COUNTRY', entity_id: 'IDN', entity_name: 'Indonesia' },
    })
    const cell = selectionReducer(country, {
      type: 'select-entity',
      entity: { entity_type: 'CELL', entity_id: 'g050_r0001_c0002', entity_name: 'g050_r0001_c0002' },
    })
    expect(cell.entity?.entity_type).toBe('CELL')
    expect(cell.area.entity_id).toBe('IDN')
  })

  it('resets the calendar to the world when the selection is cleared', () => {
    const country = selectionReducer(initialSelection, {
      type: 'select-entity',
      entity: { entity_type: 'COUNTRY', entity_id: 'IDN', entity_name: 'Indonesia' },
    })
    const cleared = selectionReducer(country, { type: 'clear-entity' })
    expect(cleared.entity).toBeNull()
    expect(cleared.area).toEqual(WORLD)
  })

  it('switches the calendar value mode', () => {
    expect(selectionReducer(initialSelection, { type: 'set-value-mode', valueMode: 'activity' }).valueMode).toBe('activity')
  })
})
