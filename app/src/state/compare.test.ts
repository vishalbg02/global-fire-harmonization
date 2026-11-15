import { describe, expect, it } from 'vitest'
import { compareFromSearch, setCompareParam } from './compare.ts'

describe('compare= in the link (T-090)', () => {
  it('reads a country, a continent and the world', () => {
    expect(compareFromSearch('?compare=COUNTRY:IDN')).toEqual({ entityType: 'COUNTRY', entityId: 'IDN' })
    expect(compareFromSearch('?area=COUNTRY:BRA&compare=CONTINENT:AS')).toEqual({ entityType: 'CONTINENT', entityId: 'AS' })
    expect(compareFromSearch('?compare=GLOBAL')).toEqual({ entityType: 'GLOBAL', entityId: 'GLOBAL' })
  })

  it('ignores a missing or invalid value, and areas the series endpoint does not serve', () => {
    for (const search of ['', '?compare=', '?compare=COUNTRY', '?compare=COUNTRY:indonesia', '?compare=CONTINENT:ASIA', '?compare=CUSTOM:1,2,3,4', '?compare=POLY:0,0;1,0;1,1', '?compare=FIRE:X']) {
      expect(compareFromSearch(search)).toBeNull()
    }
  })

  it('writes the value, and leaves the parameter out for no comparison', () => {
    const params = new URLSearchParams('area=COUNTRY:IDN&tab=analytics')
    setCompareParam(params, { entityType: 'COUNTRY', entityId: 'BRA' })
    expect(params.get('compare')).toBe('COUNTRY:BRA')
    setCompareParam(params, { entityType: 'GLOBAL', entityId: 'GLOBAL' })
    expect(params.get('compare')).toBe('GLOBAL')
    setCompareParam(params, null)
    expect(params.has('compare')).toBe(false)
    expect(params.get('area')).toBe('COUNTRY:IDN')
    expect(params.get('tab')).toBe('analytics')
  })

  it('round-trips', () => {
    const params = new URLSearchParams()
    setCompareParam(params, { entityType: 'CONTINENT', entityId: 'EU' })
    expect(compareFromSearch(`?${params.toString()}`)).toEqual({ entityType: 'CONTINENT', entityId: 'EU' })
  })
})
