import { useEffect } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import type { MapLayer } from '../api/contract.ts'
import { mapKey, mapQueryOptions, MAP_MAX_CACHED, placeholderFor, prefetchNeighbours, trimMapCache } from './mapCells.ts'
import type { MonthOption } from './months.ts'

interface Options {
  month: { year: number; month: number } | null
  layer: MapLayer
  enabled: boolean
  /** The months the picker offers, in order (the neighbours to prefetch come from this list). */
  months: readonly MonthOption[]
  /** False in the offline copy, where every month is a local file and there is no network to save. */
  prefetch: boolean
}

/**
 * The cells of the selected month (T-073): cached for the session, the previous month's cells
 * stay available (`isPlaceholderData`) while the next loads, so the map never blanks, and the
 * neighbouring months are fetched ahead once the shown month has arrived.
 */
export function useMapCells({ month, layer, enabled, months, prefetch }: Options) {
  const client = useQueryClient()
  const active = enabled && month !== null
  const query = useQuery({
    ...mapQueryOptions(month?.year ?? 0, month?.month ?? 0, layer),
    enabled: active,
    ...placeholderFor(active),
  })

  const loaded = query.isSuccess && !query.isPlaceholderData
  const year = month?.year
  const mon = month?.month
  useEffect(() => {
    if (!active || !prefetch || !loaded || year === undefined || mon === undefined) return
    trimMapCache(client, MAP_MAX_CACHED, [mapKey(year, mon, layer)])
    return prefetchNeighbours(client, months, { year, month: mon }, layer)
  }, [active, prefetch, loaded, year, mon, layer, months, client])

  return query
}
