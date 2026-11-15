// Caching and prefetching of the map months (T-073). No data is computed here: a month is the
// API's own answer, fetched once, kept for the session, and fetched ahead for the months the
// user is most likely to step to next.

import { keepPreviousData, type QueryClient, type QueryKey } from '@tanstack/react-query'
import { fetchMapCells } from '../api/client.ts'
import type { MapCell, MapLayer } from '../api/contract.ts'
import { type MonthOption } from './months.ts'

/** A fetched month does not change while the session lasts (the products are a fixed snapshot). */
export const MAP_STALE_TIME = 30 * 60 * 1000
/** How long an unused month stays in memory. */
export const MAP_GC_TIME = 30 * 60 * 1000
/** Parsed cells of a month are tens of MB in memory: keep this many months at most. */
export const MAP_MAX_CACHED = 6
/** Months fetched as soon as the selected month is shown: the previous and the next. */
export const NEAR_OFFSETS = [1, -1] as const
/** Months fetched when the browser is idle: the two beyond. */
export const FAR_OFFSETS = [2, -2] as const

type Fetcher = (year: number, month: number, layer: MapLayer) => Promise<MapCell[]>

export function mapKey(year: number | undefined, month: number | undefined, layer: MapLayer): QueryKey {
  return ['map', year, month, layer]
}

/** The query of one map month. Shared by the visible map and the prefetches so they use one cache entry. */
export function mapQueryOptions(year: number, month: number, layer: MapLayer, fetcher: Fetcher = fetchMapCells) {
  return {
    queryKey: mapKey(year, month, layer),
    queryFn: () => fetcher(year, month, layer),
    staleTime: MAP_STALE_TIME,
    gcTime: MAP_GC_TIME,
    retry: false,
  }
}

/** Options that keep the previous month's cells on screen while the next month loads. */
export function placeholderFor(enabled: boolean) {
  return enabled ? { placeholderData: keepPreviousData } : {}
}

/** The months `offsets` steps away from `current` in the picker's list (positive is later); out-of-range steps are dropped. */
export function neighbourMonths(
  months: readonly MonthOption[],
  current: { year: number; month: number },
  offsets: readonly number[],
): MonthOption[] {
  const at = months.findIndex((m) => m.year === current.year && m.month === current.month)
  if (at < 0) return []
  return offsets.flatMap((o) => {
    const m = months[at + o]
    return m === undefined ? [] : [m]
  })
}

/**
 * Drops the oldest cached map months beyond `max` (by last update), never one that is shown
 * (has an observer) or listed in `keep`. Returns how many were removed.
 */
export function trimMapCache(client: QueryClient, max: number = MAP_MAX_CACHED, keep: readonly QueryKey[] = []): number {
  const protectedKeys = new Set(keep.map((k) => JSON.stringify(k)))
  const maps = client
    .getQueryCache()
    .findAll({ queryKey: ['map'] })
    .sort((a, b) => b.state.dataUpdatedAt - a.state.dataUpdatedAt)
  let removed = 0
  let kept = 0
  for (const q of maps) {
    const pinned = q.getObserversCount() > 0 || protectedKeys.has(JSON.stringify(q.queryKey))
    if (pinned || kept < max) {
      kept += 1
      continue
    }
    client.removeQueries({ queryKey: q.queryKey, exact: true })
    removed += 1
  }
  return removed
}

type Schedule = (task: () => void) => () => void

/** Runs `task` when the browser is idle (or soon after, where there is no idle callback). */
export const whenIdle: Schedule = (task) => {
  const g = globalThis as { requestIdleCallback?: (cb: () => void) => number; cancelIdleCallback?: (id: number) => void }
  if (typeof g.requestIdleCallback === 'function') {
    const id = g.requestIdleCallback(task)
    return () => g.cancelIdleCallback?.(id)
  }
  const id = setTimeout(task, 300)
  return () => clearTimeout(id)
}

/**
 * Fetches the neighbours of `current` for the layer in use: the previous and next month at once,
 * the two beyond when idle, one after the other so the server is not asked for everything together.
 * A month that is already fresh is not fetched again. Failures are ignored (the month is then
 * fetched normally when the user steps to it). Returns a function that cancels what is still waiting.
 */
export function prefetchNeighbours(
  client: QueryClient,
  months: readonly MonthOption[],
  current: { year: number; month: number },
  layer: MapLayer,
  options: { fetcher?: Fetcher; schedule?: Schedule } = {},
): () => void {
  const fetcher = options.fetcher ?? fetchMapCells
  const schedule = options.schedule ?? whenIdle
  let cancelled = false
  let cancelIdle: (() => void) | null = null
  const load = (m: MonthOption) =>
    client.prefetchQuery(mapQueryOptions(m.year, m.month, layer, fetcher)).catch(() => undefined)

  const near = neighbourMonths(months, current, NEAR_OFFSETS)
  const far = neighbourMonths(months, current, FAR_OFFSETS)
  void Promise.all(near.map(load)).then(() => {
    if (cancelled) return
    cancelIdle = schedule(() => {
      void (async () => {
        for (const m of far) {
          if (cancelled) return
          await load(m)
        }
        if (!cancelled) trimMapCache(client, MAP_MAX_CACHED, [mapKey(current.year, current.month, layer)])
      })()
    })
  })
  return () => {
    cancelled = true
    cancelIdle?.()
  }
}
