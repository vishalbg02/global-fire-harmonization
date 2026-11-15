/**
 * The area compared with in the Analytics tab (T-090), kept in the link as `compare=`: `COUNTRY:IDN`, `CONTINENT:AS` or `GLOBAL`.
 * Only the areas the series endpoint serves; anything else in a link is ignored, never an error.
 */
export const COMPARE_PARAM = 'compare'

export interface CompareRef {
  entityType: 'COUNTRY' | 'CONTINENT' | 'GLOBAL'
  entityId: string
}

const COUNTRY_ID = /^[A-Z0-9]{2,3}$/
const CONTINENT_ID = /^[A-Z]{2}$/

/** The comparison a link asks for, or null for a missing or invalid value. */
export function compareFromSearch(search: string): CompareRef | null {
  const text = new URLSearchParams(search).get(COMPARE_PARAM)
  if (text === null) return null
  if (text === 'GLOBAL') return { entityType: 'GLOBAL', entityId: 'GLOBAL' }
  const colon = text.indexOf(':')
  if (colon < 0) return null
  const kind = text.slice(0, colon)
  const id = text.slice(colon + 1)
  if (kind === 'COUNTRY' && COUNTRY_ID.test(id)) return { entityType: 'COUNTRY', entityId: id }
  if (kind === 'CONTINENT' && CONTINENT_ID.test(id)) return { entityType: 'CONTINENT', entityId: id }
  return null
}

/** Writes the comparison into link parameters; no comparison leaves the parameter out. */
export function setCompareParam(params: URLSearchParams, compare: CompareRef | null): void {
  if (compare === null) params.delete(COMPARE_PARAM)
  else params.set(COMPARE_PARAM, compare.entityType === 'GLOBAL' ? 'GLOBAL' : `${compare.entityType}:${compare.entityId}`)
}
