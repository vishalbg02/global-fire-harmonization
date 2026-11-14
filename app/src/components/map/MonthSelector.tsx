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
  const go = (i: number) => {
    const m = months[i]
    if (m !== undefined) onChange(m.year, m.month)
  }
  return (
    <div className="month-selector" role="group" aria-label="Month">
      <button type="button" onClick={() => go(index - 1)} disabled={index <= 0} aria-label="Previous month">
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
      <button type="button" onClick={() => go(index + 1)} disabled={index < 0 || index >= months.length - 1} aria-label="Next month">
        ▶
      </button>
      <output aria-live="polite">
        {current === null ? 'No month available' : monthLabel(current)}
        {current?.provisional === true && <span className="badge"> Provisional</span>}
      </output>
    </div>
  )
}
