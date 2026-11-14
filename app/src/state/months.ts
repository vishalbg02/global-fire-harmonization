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
