import { useEffect, useId, useRef, useState } from 'react'
import type { KeyboardEvent } from 'react'
import * as T from '../../content/monthPicker.ts'
import { monthKey, monthLabel } from '../../state/months.ts'
import type { MonthOption } from '../../state/months.ts'
import { monthStatus, parseMonthInput, yearsOf } from './monthPicker.ts'
import './monthPicker.css'

interface Props {
  months: readonly MonthOption[]
  value: { year: number; month: number } | null
  /** A month was chosen (a button, or typed text that names a month of the record). */
  onChoose: (year: number, month: number) => void
  onClose: () => void
}

/** Scroll the list itself (not the page) so that the row of `year` is at its top. */
function scrollListToYear(list: HTMLElement | null, year: number, smooth: boolean) {
  const row = list?.querySelector<HTMLElement>(`[data-year="${year}"]`)
  if (list !== null && row !== null && row !== undefined) {
    list.scrollTo?.({ top: row.offsetTop - list.offsetTop, behavior: smooth ? 'smooth' : 'auto' })
  }
}

/**
 * The month picker (T-087): every year of the record as a row of 12 month buttons, a year select that jumps to a year, and a text
 * field for a typed month. Open it, press a month: two clicks for any month. Months outside the record are disabled, provisional
 * months carry a dot.
 */
export function MonthPicker({ months, value, onChoose, onClose }: Props) {
  const years = yearsOf(months)
  const titleId = useId()
  const errorId = useId()
  const listRef = useRef<HTMLDivElement>(null)
  const [typed, setTyped] = useState('')
  const [invalid, setInvalid] = useState(false)
  const selectedYear = value?.year ?? years[years.length - 1] ?? 0
  const first = months[0]
  const last = months[months.length - 1]

  const scrollToYear = (year: number, smooth = false) => scrollListToYear(listRef.current, year, smooth)
  const [initialYear] = useState(selectedYear)

  // Open on the current year, and move the focus to the selected month (or the first available one).
  useEffect(() => {
    scrollListToYear(listRef.current, initialYear, false)
    const target =
      listRef.current?.querySelector<HTMLButtonElement>('button[aria-pressed="true"]') ??
      listRef.current?.querySelector<HTMLButtonElement>('button:not(:disabled)')
    target?.focus({ preventScroll: true })
  }, [initialYear])

  const submit = () => {
    const parsed = parseMonthInput(typed)
    if (parsed !== null && monthStatus(months, parsed) !== 'outside') {
      setInvalid(false)
      onChoose(parsed.year, parsed.month)
    } else setInvalid(true)
  }

  const onKeyDown = (e: KeyboardEvent<HTMLDivElement>) => {
    if (e.key === 'Escape') {
      e.preventDefault()
      e.stopPropagation()
      onClose()
    }
  }

  return (
    <div className="month-picker" role="dialog" aria-modal="false" aria-labelledby={titleId} onKeyDown={onKeyDown}>
      <div className="month-picker-head">
        <h2 id={titleId} className="month-picker-title">
          {T.PICKER_TITLE}
        </h2>
        <button type="button" className="btn btn-secondary month-picker-close" onClick={onClose}>
          {T.PICKER_CLOSE}
        </button>
      </div>
      <div className="month-picker-tools">
        <label className="month-picker-field">
          <span>{T.PICKER_YEAR_LABEL}</span>
          <select aria-label={T.PICKER_YEAR_LABEL} value={selectedYear} onChange={(e) => scrollToYear(Number(e.target.value), true)}>
            {[...years].reverse().map((y) => (
              <option key={y} value={y}>
                {y}
              </option>
            ))}
          </select>
        </label>
        <form
          className="month-picker-field month-picker-type"
          onSubmit={(e) => {
            e.preventDefault()
            submit()
          }}
        >
          <label>
            <span>{T.PICKER_TYPE_LABEL}</span>
            <input
              type="text"
              inputMode="numeric"
              autoComplete="off"
              value={typed}
              placeholder={T.PICKER_TYPE_PLACEHOLDER}
              aria-invalid={invalid || undefined}
              aria-describedby={invalid ? errorId : undefined}
              onChange={(e) => {
                setTyped(e.target.value)
                setInvalid(false)
              }}
            />
          </label>
          <button type="submit" className="btn btn-secondary">
            {T.PICKER_GO}
          </button>
        </form>
      </div>
      {invalid && first !== undefined && last !== undefined && (
        <p id={errorId} role="alert" className="month-picker-error">
          {T.invalidMonthMessage(monthKey(first.year, first.month), monthKey(last.year, last.month))}
        </p>
      )}
      <div className="month-picker-list" ref={listRef}>
        {years.map((year) => (
          <div key={year} className="month-picker-row" role="group" aria-label={String(year)} data-year={year}>
            <span className="month-picker-year" aria-hidden="true">
              {year}
            </span>
            {T.MONTH_ABBREVIATIONS.map((abbreviation, i) => {
              const month = i + 1
              const status = monthStatus(months, { year, month })
              const selected = value?.year === year && value.month === month
              return (
                <button
                  key={month}
                  type="button"
                  className={`month-picker-month${status === 'provisional' ? ' is-provisional' : ''}`}
                  disabled={status === 'outside'}
                  aria-pressed={selected}
                  aria-label={`${monthLabel({ year, month })}${status === 'provisional' ? `, ${T.PROVISIONAL_MARK}` : ''}`}
                  onClick={() => onChoose(year, month)}
                >
                  {abbreviation}
                </button>
              )
            })}
          </div>
        ))}
      </div>
      <p className="month-picker-legend">{T.PICKER_LEGEND}</p>
    </div>
  )
}
