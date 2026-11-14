import { describe, expect, it } from 'vitest'
import { monthKey, monthRange } from './months.ts'
import { initialSelection, selectionReducer } from './selection.ts'

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
  it('starts with no entity, no month and the verdict layer', () => {
    expect(initialSelection).toEqual({ entity: null, month: null, layer: 'verdict' })
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
    expect(s2).toEqual({ entity: null, month: { year: 2015, month: 9 }, layer: 'raw' })
  })
})
