import { useEffect, useId, useRef, useState } from 'react'
import type { KeyboardEvent } from 'react'
import * as T from '../../content/monthPicker.ts'
import * as UI from '../../content/ui.ts'
import { monthLabel } from '../../state/months.ts'
import type { MonthOption } from '../../state/months.ts'
import { MonthPicker } from './MonthPicker.tsx'
import { applyKeyAction, keyAction, shiftYear, yearTicks } from './monthPicker.ts'
import { PLAY_INTERVAL_MS, nextPlayIndex, playStartIndex, useReducedMotion } from './playback.ts'

interface Props {
  /** Available months, in order. Passed in; wired to the metadata by the caller. */
  months: readonly MonthOption[]
  value: { year: number; month: number } | null
  onChange: (year: number, month: number) => void
}

export function MonthSelector({ months, value, onChange }: Props) {
  const index = value === null ? -1 : months.findIndex((m) => m.year === value.year && m.month === value.month)
  const current = index >= 0 ? months[index] : null
  const noteId = useId()
  const [playing, setPlaying] = useState(false)
  const [pickerOpen, setPickerOpen] = useState(false)
  const pickerId = useId()
  const rootRef = useRef<HTMLDivElement>(null)
  const triggerRef = useRef<HTMLButtonElement>(null)
  const reduced = useReducedMotion()
  const latestOnChange = useRef(onChange)
  useEffect(() => {
    latestOnChange.current = onChange
  })
  // A month that is not in the list (the offline copy has the map for some months only, but the
  // calendar can select any): show it, and move to the nearest listed month on either side.
  const outside = index < 0 && value !== null && months.length > 0
  const before = outside ? months.filter((m) => m.year * 12 + m.month < value.year * 12 + value.month) : []
  const after = outside ? months.filter((m) => m.year * 12 + m.month > value.year * 12 + value.month) : []
  const go = (i: number) => {
    const m = months[i]
    if (m !== undefined) onChange(m.year, m.month)
  }
  // Any manual choice pauses the time-lapse.
  const manual = (fn: () => void) => {
    setPlaying(false)
    fn()
  }
  const step = (direction: -1 | 1) => {
    if (outside) {
      const target = direction < 0 ? before[before.length - 1] : after[0]
      if (target !== undefined) onChange(target.year, target.month)
    } else go(index + direction)
  }
  const canBack = outside ? before.length > 0 : index > 0
  const canForward = outside ? after.length > 0 : index >= 0 && index < months.length - 1

  // The time-lapse: one month per interval, paused at the last month.
  useEffect(() => {
    if (!playing || reduced) return
    const next = nextPlayIndex(index, months.length)
    const timer = setTimeout(() => {
      if (next === null) setPlaying(false)
      else {
        const m = months[next]
        if (m !== undefined) latestOnChange.current(m.year, m.month)
      }
    }, PLAY_INTERVAL_MS)
    return () => clearTimeout(timer)
  }, [playing, reduced, index, months])

  const togglePlay = () => {
    if (playing) return setPlaying(false)
    if (months.length === 0 || reduced) return
    const start = playStartIndex(index, months.length)
    if (start !== index) go(start)
    setPlaying(true)
  }

  const jumpYear = (delta: -1 | 1) => {
    if (value === null || index < 0) return
    const to = shiftYear(months, value, delta)
    if (to !== null && (to.year !== value.year || to.month !== value.month)) onChange(to.year, to.month)
  }
  const canYear = (delta: -1 | 1) => {
    if (value === null || index < 0) return false
    const to = shiftYear(months, value, delta)
    return to !== null && (to.year !== value.year || to.month !== value.month)
  }

  // Close the picker and return the focus to its button.
  const closePicker = () => {
    setPickerOpen(false)
    triggerRef.current?.focus()
  }
  useEffect(() => {
    if (!pickerOpen) return
    const onDown = (e: MouseEvent) => {
      if (rootRef.current !== null && !rootRef.current.contains(e.target as Node)) setPickerOpen(false)
    }
    document.addEventListener('mousedown', onDown)
    return () => document.removeEventListener('mousedown', onDown)
  }, [pickerOpen])

  // Arrows step the month from the buttons too (the slider has them natively); Page Up and Page Down move a year, Home and End go
  // to the first and last month, also on the slider (which would otherwise page by a tenth of the range). Text fields and the
  // picker keep their own keys.
  const onKeyDown = (e: KeyboardEvent<HTMLDivElement>) => {
    const target = e.target as HTMLElement
    const isRange = target.tagName === 'INPUT' && (target as HTMLInputElement).type === 'range'
    if (target.closest('.month-picker') !== null || target.tagName === 'SELECT' || (target.tagName === 'INPUT' && !isRange)) return
    const action = keyAction(e.key)
    if (action === null || value === null || index < 0) return
    if (isRange && action.type === 'month') return // the slider handles the arrows itself
    e.preventDefault()
    const to = applyKeyAction(months, value, action)
    if (to !== null) manual(() => onChange(to.year, to.month))
  }

  return (
    <div className="month-selector" role="group" aria-label="Month" onKeyDown={onKeyDown} ref={rootRef}>
      <button
        type="button"
        className="btn btn-secondary btn-icon play"
        onClick={togglePlay}
        disabled={months.length === 0}
        aria-disabled={reduced || undefined}
        aria-pressed={playing}
        aria-label={playing ? UI.PAUSE_LABEL : UI.PLAY_LABEL}
        aria-describedby={reduced ? noteId : undefined}
      >
        <span aria-hidden="true">{playing ? '❚❚' : '▶'}</span>
        <span className="play-text">{playing ? UI.PAUSE : UI.PLAY}</span>
      </button>
      <button
        type="button"
        className="btn btn-secondary btn-icon month-year-step"
        onClick={() => manual(() => jumpYear(-1))}
        disabled={!canYear(-1)}
        aria-label={T.PREVIOUS_YEAR_LABEL}
        title={T.PREVIOUS_YEAR_LABEL}
      >
        ◀◀
      </button>
      <button
        type="button"
        className="btn btn-secondary btn-icon"
        onClick={() => manual(() => step(-1))}
        disabled={!canBack}
        aria-label="Previous month"
      >
        ◀
      </button>
      <div className="month-slider">
        <input
          type="range"
          min={0}
          max={Math.max(months.length - 1, 0)}
          value={Math.max(index, 0)}
          disabled={months.length === 0}
          onChange={(e) => manual(() => go(Number(e.target.value)))}
          aria-label="Month slider"
          aria-valuetext={current === null ? 'No month selected' : monthLabel(current)}
          aria-describedby={`${pickerId}-hint`}
        />
        <div className="month-ticks" aria-hidden="true">
          {yearTicks(months).map((tick) => (
            <span key={tick.year} className={tick.labelled ? 'month-tick is-labelled' : 'month-tick'} style={{ left: `${tick.percent}%` }}>
              {tick.labelled ? <span className="month-tick-label">{tick.year}</span> : null}
            </span>
          ))}
        </div>
        <span id={`${pickerId}-hint`} className="month-hint">
          {T.SLIDER_HINT}
        </span>
      </div>
      <button
        type="button"
        className="btn btn-secondary btn-icon"
        onClick={() => manual(() => step(1))}
        disabled={!canForward}
        aria-label="Next month"
      >
        ▶
      </button>
      <button
        type="button"
        className="btn btn-secondary btn-icon month-year-step"
        onClick={() => manual(() => jumpYear(1))}
        disabled={!canYear(1)}
        aria-label={T.NEXT_YEAR_LABEL}
        title={T.NEXT_YEAR_LABEL}
      >
        ▶▶
      </button>
      <output aria-live={playing ? 'off' : 'polite'} className="month-value">
        {current === null
          ? outside
            ? `${monthLabel(value)} (no offline map)`
            : 'No month available'
          : monthLabel(current)}
        {current?.provisional === true && <span className="badge"> Provisional</span>}
      </output>
      <button
        type="button"
        ref={triggerRef}
        className="btn btn-secondary month-picker-trigger"
        aria-haspopup="dialog"
        aria-expanded={pickerOpen}
        aria-controls={pickerOpen ? pickerId : undefined}
        disabled={months.length === 0}
        onClick={() => {
          setPlaying(false)
          setPickerOpen((open) => !open)
        }}
      >
        {T.PICKER_OPEN_LABEL} <span aria-hidden="true">▾</span>
      </button>
      {pickerOpen && (
        <div id={pickerId} className="month-picker-anchor">
          <MonthPicker
            months={months}
            value={value}
            onChoose={(year, month) => {
              onChange(year, month)
              closePicker()
            }}
            onClose={closePicker}
          />
        </div>
      )}
      {reduced && (
        <p id={noteId} className="month-note">
          {UI.REDUCED_MOTION_NOTE}
        </p>
      )}
    </div>
  )
}
