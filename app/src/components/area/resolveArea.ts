import type { EntityItem } from '../../api/contract.ts'
import type { Area } from '../../state/selection.ts'

/**
 * Fills in the display name of a country or continent that came from a link (where only the
 * id is known) from the entity lists. Other areas, and ids not in the lists, are unchanged.
 */
export function resolveArea(
  area: Area,
  countries: readonly EntityItem[] | undefined,
  continents: readonly EntityItem[] | undefined,
): Area {
  if (area.entity_type === 'COUNTRY' || area.entity_type === 'CONTINENT') {
    const list = area.entity_type === 'COUNTRY' ? countries : continents
    const found = list?.find((e) => e.entity_id === area.entity_id)
    if (found !== undefined && found.entity_name !== area.entity_name) {
      return { ...area, entity_name: found.entity_name }
    }
  }
  return area
}
