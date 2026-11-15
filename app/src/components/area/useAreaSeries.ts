import { useQuery } from '@tanstack/react-query'
import { fetchCustomSeries, fetchSeries } from '../../api/client.ts'
import type { Area } from '../../state/selection.ts'

/**
 * The monthly series of the selected area: the series endpoint for a country, a continent or
 * the world, and `POST /api/series/custom` for a custom rectangle. The calendar and the
 * evidence panel share one query (same key), so a custom area triggers one request.
 */
export function useAreaSeries(area: Area, options: { enabled?: boolean } = {}) {
  const key =
    area.entity_type === 'CUSTOM'
      ? area.polygon === undefined
        ? ['series-custom', ...area.bbox]
        : ['series-custom-polygon', area.entity_id]
      : ['series', area.entity_type, area.entity_id]
  return useQuery({
    queryKey: key,
    queryFn: () =>
      area.entity_type === 'CUSTOM'
        ? fetchCustomSeries(area.polygon === undefined ? area.bbox : { polygon: area.polygon })
        : fetchSeries(area.entity_type, area.entity_id),
    enabled: options.enabled ?? true,
    retry: false,
  })
}
