import type { Bbox, EntityItem } from '../../api/contract.ts'
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

/**
 * The box the map should show for the selected area: a country or continent (from the entity
 * lists, once they are loaded, also for an area that came from a link or a click on the map) or a
 * custom area. The world and a single cell give null: the map keeps its view (the World button
 * asks for its own fit).
 */
export function areaFitBbox(
  area: Area,
  countries: readonly EntityItem[] | undefined,
  continents: readonly EntityItem[] | undefined,
): Bbox | null {
  if (area.entity_type === 'CUSTOM') return area.bbox
  if (area.entity_type === 'COUNTRY' || area.entity_type === 'CONTINENT') {
    const list = area.entity_type === 'COUNTRY' ? countries : continents
    return list?.find((e) => e.entity_id === area.entity_id)?.bbox ?? null
  }
  return null
}
