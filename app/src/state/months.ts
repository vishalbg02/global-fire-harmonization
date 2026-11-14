export interface MonthOption {
  year: number
  month: number
  provisional: boolean
}

function parse(ym: string): { year: number; month: number } {
  const [y, m] = ym.split('-')
  return { year: Number(y), month: Number(m) }
}

export function monthKey(year: number, month: number): string {
  return `${year}-${String(month).padStart(2, '0')}`
}

/** Every month from `first` to `latest` inclusive (both "YYYY-MM"), marking provisional ones. */
export function monthRange(first: string, latest: string, provisional: readonly string[]): MonthOption[] {
  const start = parse(first)
  const end = parse(latest)
  const marked = new Set(provisional)
  const months: MonthOption[] = []
  let { year, month } = start
  while (year < end.year || (year === end.year && month <= end.month)) {
    months.push({ year, month, provisional: marked.has(monthKey(year, month)) })
    month += 1
    if (month > 12) {
      month = 1
      year += 1
    }
  }
  return months
}

const MONTH_NAMES = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December']

export function monthLabel(m: { year: number; month: number }): string {
  return `${MONTH_NAMES[m.month - 1]} ${m.year}`
}

/**
 * The months that have a map in the offline copy: the manifest's list, in the order of `all`
 * (so the provisional marks stay). `null` (the live service, or a copy of the full data range)
 * keeps every month. The calendar, series, evidence and CSVs are not limited by this (T-043).
 */
export function offlineMapMonths(
  all: readonly MonthOption[],
  manifestMonths: readonly string[] | null,
): MonthOption[] {
  if (manifestMonths === null) return [...all]
  const listed = new Set(manifestMonths)
  return all.filter((m) => listed.has(monthKey(m.year, m.month)))
}

/** True when the month has a map (always, outside the offline copy). */
export function hasOfflineMap(
  manifestMonths: readonly string[] | null,
  month: { year: number; month: number } | null,
): boolean {
  return manifestMonths === null || month === null || manifestMonths.includes(monthKey(month.year, month.month))
}
