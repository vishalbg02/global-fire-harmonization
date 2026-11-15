import { useEffect } from 'react'
import { useAreaSeries } from '../components/area/useAreaSeries.ts'
import type { MonthOption } from './months.ts'
import { WORLD } from './selection.ts'

/** The fields of a series record the rule reads. */
export interface DeterminableRecord {
  year: number
  month: number
  estimate: number | null
  reason_codes: readonly string[]
}

export interface YearMonth {
  year: number
  month: number
}

/**
 * The month the app opens on (T-071): the latest month of the GLOBAL series whose record has an
 * estimate and no OUTAGE reason (a provisional month with an estimate counts). The newest month
 * can be all "cannot determine" (an outage), which would show a grey world on first load.
 * Falls back to `fallback` (the latest month in the metadata) when no month qualifies. Display
 * only: nothing is computed or changed in the data.
 */
export function latestDeterminableMonth(
  series: readonly DeterminableRecord[],
  fallback: YearMonth | null,
): YearMonth | null {
  let best: YearMonth | null = null
  for (const r of series) {
    if (r.estimate === null || r.reason_codes.includes('OUTAGE')) continue
    if (best === null || r.year > best.year || (r.year === best.year && r.month > best.month)) {
      best = { year: r.year, month: r.month }
    }
  }
  return best ?? fallback
}

/**
 * Start on the latest determinable month once the months and the world series are known. Does
 * nothing when a month is already set (a month in the link wins). If the series cannot be loaded
 * it starts on the latest month, as before.
 */
export function useStartMonth(
  months: readonly MonthOption[],
  month: YearMonth | null,
  onStart: (year: number, month: number) => void,
): void {
  const world = useAreaSeries(WORLD, { enabled: month === null && months.length > 0 })
  useEffect(() => {
    const latest = months[months.length - 1]
    if (month !== null || latest === undefined || world.isPending) return
    const pick = latestDeterminableMonth(world.data ?? [], latest)
    const listed = pick !== null && months.some((m) => m.year === pick.year && m.month === pick.month)
    const start = listed ? pick : latest
    onStart(start.year, start.month)
    // eslint-disable-next-line react-hooks/exhaustive-deps -- onStart is a stable dispatch wrapper
  }, [months, month, world.isPending, world.data])
}
