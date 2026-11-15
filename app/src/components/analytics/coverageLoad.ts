import { fetchCellAreas } from '../../api/client.ts'
import type { MapCell } from '../../api/contract.ts'
import type { CellAreas } from '../../api/mapColumns.ts'
import { coverage, coverageInArea } from './compute.ts'
import type { Coverage } from './compute.ts'

export type CoverageResult =
  | { status: 'ready'; coverage: Coverage | null }
  /** The API (or the offline copy) does not send each cell's country and continent: no figure, and the panel says so. */
  | { status: 'areas-missing' }

type CellRef = Pick<MapCell, 'cell_id' | 'verdict'>

/**
 * The coverage of the selected area in the month whose cells the app already holds (`cells`, the map's columnar cache: it carries no
 * country, by design, so the areas come from the shared cell list through `getAreas`, never from these cells). The world counts every
 * cell; a country or continent counts the cells stored for it.
 */
export async function loadCoverage(
  area: { entityType: 'COUNTRY' | 'CONTINENT' | 'GLOBAL'; entityId: string },
  cells: readonly CellRef[],
  getAreas: () => Promise<CellAreas | null> = fetchCellAreas,
): Promise<CoverageResult> {
  if (area.entityType === 'GLOBAL') {
    return { status: 'ready', coverage: coverage(cells as readonly MapCell[], null) }
  }
  const areas = await getAreas()
  if (areas === null) return { status: 'areas-missing' }
  return { status: 'ready', coverage: coverageInArea(cells, areas, area.entityType, area.entityId) }
}
