import { monthLabel } from '../../state/months.ts'
import type { MonthOption } from '../../state/months.ts'

interface Props {
  /** Available months, in order. Passed in; wired to the metadata by the caller. */
  months: readonly MonthOption[]
  value: { year: number; month: number } | null
  onChange: (year: number, month: number) => void
}

export function MonthSelector({ months, value, onChange }: Props) {
  const index = value === null ? -1 : months.findIndex((m) => m.year === value.year && m.month === value.month)
  const current = index >= 0 ? months[index] : null
  // A month that is not in the list (the offline copy has the map for some months only, but the
  // calendar can select any): show it, and move to the nearest listed month on either side.
  const outside = index < 0 && value !== null && months.length > 0
  const before = outside ? months.filter((m) => m.year * 12 + m.month < value.year * 12 + value.month) : []
  const after = outside ? months.filter((m) => m.year * 12 + m.month > value.year * 12 + value.month) : []
  const go = (i: number) => {
    const m = months[i]
    if (m !== undefined) onChange(m.year, m.month)
  }
  const step = (direction: -1 | 1) => {
    if (outside) {
      const target = direction < 0 ? before[before.length - 1] : after[0]
      if (target !== undefined) onChange(target.year, target.month)
    } else go(index + direction)
  }
  const canBack = outside ? before.length > 0 : index > 0
  const canForward = outside ? after.length > 0 : index >= 0 && index < months.length - 1
  return (
    <div className="month-selector" role="group" aria-label="Month">
      <button type="button" onClick={() => step(-1)} disabled={!canBack} aria-label="Previous month">
        ◀
      </button>
      <input
        type="range"
        min={0}
        max={Math.max(months.length - 1, 0)}
        value={Math.max(index, 0)}
        disabled={months.length === 0}
        onChange={(e) => go(Number(e.target.value))}
        aria-label="Month slider"
        aria-valuetext={current === null ? 'No month selected' : monthLabel(current)}
      />
      <button type="button" onClick={() => step(1)} disabled={!canForward} aria-label="Next month">
        ▶
      </button>
      <output aria-live="polite">
        {current === null
          ? outside
            ? `${monthLabel(value)} (no offline map)`
            : 'No month available'
          : monthLabel(current)}
        {current?.provisional === true && <span className="badge"> Provisional</span>}
      </output>
    </div>
  )
}
