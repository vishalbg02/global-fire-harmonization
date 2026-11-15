import { QueryClient, QueryObserver } from '@tanstack/react-query'
import { describe, expect, it } from 'vitest'
import type { MapCell, MapLayer } from '../api/contract.ts'
import {
  MAP_STALE_TIME,
  mapKey,
  mapQueryOptions,
  neighbourMonths,
  placeholderFor,
  prefetchNeighbours,
  trimMapCache,
} from './mapCells.ts'
import { monthKey, monthRange } from './months.ts'

// SYNTHETIC test data: a made-up list of months and fake map months (a one-element list per month
// that carries its own label), with a recording fetcher instead of the network.
const MONTHS = monthRange('2020-01', '2021-12', [])
const cellsOf = (year: number, month: number) => [{ cell_id: monthKey(year, month) }] as unknown as MapCell[]

function recorder() {
  const calls: string[] = []
  const fetcher = async (year: number, month: number, layer: MapLayer) => {
    calls.push(`${monthKey(year, month)}/${layer}`)
    return cellsOf(year, month)
  }
  return { calls, fetcher }
}

const now = (schedule: () => void) => {
  schedule()
  return () => {}
}
const flush = () => new Promise((r) => setTimeout(r, 0))

describe('neighbour months', () => {
  it('lists the months at the given steps, in the picker order, dropping those out of range', () => {
    const at = (y: number, m: number, o: number[]) => neighbourMonths(MONTHS, { year: y, month: m }, o).map((x) => monthKey(x.year, x.month))
    expect(at(2020, 6, [1, -1])).toEqual(['2020-07', '2020-05'])
    expect(at(2020, 12, [1, -1, 2, -2])).toEqual(['2021-01', '2020-11', '2021-02', '2020-10'])
    expect(at(2020, 1, [1, -1, 2, -2])).toEqual(['2020-02', '2020-03'])
    expect(at(2021, 12, [1, -1, 2, -2])).toEqual(['2021-11', '2021-10'])
  })

  it('has none for a month that is not in the list', () => {
    expect(neighbourMonths(MONTHS, { year: 1999, month: 1 }, [1, -1])).toEqual([])
  })
})

describe('prefetching the neighbours', () => {
  it('fetches the previous and next month at once and the two beyond when idle, for the layer in use', async () => {
    const client = new QueryClient()
    const { calls, fetcher } = recorder()
    const idleTasks: (() => void)[] = []
    prefetchNeighbours(client, MONTHS, { year: 2020, month: 6 }, 'raw', {
      fetcher,
      schedule: (task) => {
        idleTasks.push(task)
        return () => {}
      },
    })
    await flush()
    expect([...calls].sort()).toEqual(['2020-05/raw', '2020-07/raw'])
    expect(idleTasks).toHaveLength(1)
    idleTasks[0]!()
    await flush()
    await flush()
    expect([...calls].sort()).toEqual(['2020-04/raw', '2020-05/raw', '2020-07/raw', '2020-08/raw'])
    expect(client.getQueryData(mapKey(2020, 7, 'raw'))).toEqual(cellsOf(2020, 7))
  })

  it('does not fetch a month that is already fresh, and a month for another layer is another entry', async () => {
    const client = new QueryClient()
    const { calls, fetcher } = recorder()
    await client.prefetchQuery(mapQueryOptions(2020, 7, 'verdict', fetcher))
    calls.length = 0
    prefetchNeighbours(client, MONTHS, { year: 2020, month: 6 }, 'verdict', { fetcher, schedule: now })
    await flush()
    await flush()
    expect(calls).not.toContain('2020-07/verdict')
    expect(calls).toContain('2020-05/verdict')
    expect(client.getQueryData(mapKey(2020, 7, 'raw'))).toBeUndefined()
  })

  it('stops when cancelled: the idle step never runs', async () => {
    const client = new QueryClient()
    const { calls, fetcher } = recorder()
    let idleCancelled = false
    const cancel = prefetchNeighbours(client, MONTHS, { year: 2020, month: 6 }, 'raw', {
      fetcher,
      schedule: () => () => {
        idleCancelled = true
      },
    })
    await flush()
    cancel()
    expect(idleCancelled).toBe(true)
    expect(calls).toHaveLength(2)
  })

  it('ignores a failing fetch (no unhandled rejection) and keeps going', async () => {
    const client = new QueryClient()
    const seen: string[] = []
    const fetcher = async (year: number, month: number) => {
      seen.push(monthKey(year, month))
      if (month === 7) throw new Error('network')
      return cellsOf(year, month)
    }
    prefetchNeighbours(client, MONTHS, { year: 2020, month: 6 }, 'raw', { fetcher, schedule: now })
    await flush()
    await flush()
    expect(seen).toEqual(expect.arrayContaining(['2020-05', '2020-07', '2020-04', '2020-08']))
    expect(client.getQueryData(mapKey(2020, 5, 'raw'))).toBeDefined()
    expect(client.getQueryData(mapKey(2020, 7, 'raw'))).toBeUndefined()
  })
})

describe('the cache of months', () => {
  it('keeps a fetched month fresh for the session: a second ask does not fetch again', async () => {
    const client = new QueryClient()
    const { calls, fetcher } = recorder()
    expect(mapQueryOptions(2020, 1, 'raw', fetcher).staleTime).toBe(MAP_STALE_TIME)
    await client.fetchQuery(mapQueryOptions(2020, 1, 'raw', fetcher))
    await client.fetchQuery(mapQueryOptions(2020, 1, 'raw', fetcher))
    expect(calls).toEqual(['2020-01/raw'])
  })

  it('keeps at most N months, dropping the oldest, never the protected or the shown one', async () => {
    const client = new QueryClient()
    const { fetcher } = recorder()
    for (let m = 1; m <= 8; m += 1) {
      await client.fetchQuery(mapQueryOptions(2020, m, 'raw', fetcher))
      await new Promise((r) => setTimeout(r, 2)) // distinct update times
    }
    const shown = new QueryObserver(client, mapQueryOptions(2020, 1, 'raw', fetcher))
    const unsubscribe = shown.subscribe(() => {})
    const removed = trimMapCache(client, 3, [mapKey(2020, 2, 'raw')])
    unsubscribe()
    const left = client.getQueryCache().findAll({ queryKey: ['map'] }).map((q) => q.queryKey[2]).sort()
    // observed month 1 and protected month 2 stay; of the rest the 3 newest (8, 7, 6) fit within max
    expect(removed).toBe(3)
    expect(left).toEqual([1, 2, 6, 7, 8])
  })
})

describe('the map never blanks while the next month loads', () => {
  it('keeps the previous month’s cells as placeholder data until the next month arrives', async () => {
    const client = new QueryClient()
    let release: () => void = () => {}
    const gate = new Promise<void>((r) => {
      release = r
    })
    const fetcher = async (year: number, month: number) => {
      if (month === 2) await gate
      return cellsOf(year, month)
    }
    const options = (month: number) => ({ ...mapQueryOptions(2020, month, 'raw', fetcher), ...placeholderFor(true) })
    const observer = new QueryObserver(client, options(1))
    const unsubscribe = observer.subscribe(() => {})
    await flush()
    expect(observer.getCurrentResult().data).toEqual(cellsOf(2020, 1))

    observer.setOptions(options(2))
    const during = observer.getCurrentResult()
    expect(during.isPlaceholderData).toBe(true)
    expect(during.data).toEqual(cellsOf(2020, 1))

    release()
    await flush()
    const after = observer.getCurrentResult()
    expect(after.isPlaceholderData).toBe(false)
    expect(after.data).toEqual(cellsOf(2020, 2))
    unsubscribe()
  })

  it('shows nothing, not the old month, when the query is disabled', () => {
    const client = new QueryClient()
    const { fetcher } = recorder()
    const observer = new QueryObserver(client, { ...mapQueryOptions(2020, 1, 'raw', fetcher), enabled: false, ...placeholderFor(false) })
    expect(observer.getCurrentResult().data).toBeUndefined()
    expect(placeholderFor(false)).toEqual({})
  })

  it('a prefetched month is shown at once, with no request', async () => {
    const client = new QueryClient()
    const { calls, fetcher } = recorder()
    await client.prefetchQuery(mapQueryOptions(2020, 7, 'raw', fetcher))
    calls.length = 0
    const observer = new QueryObserver(client, { ...mapQueryOptions(2020, 7, 'raw', fetcher), ...placeholderFor(true) })
    const result = observer.getCurrentResult()
    expect(result.data).toEqual(cellsOf(2020, 7))
    expect(result.isPlaceholderData).toBe(false)
    const unsubscribe = observer.subscribe(() => {})
    await flush()
    unsubscribe()
    expect(calls).toEqual([])
  })
})
