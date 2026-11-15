import { useEffect, useId, useRef, useState } from 'react'
import type { KeyboardEvent } from 'react'
import * as UI from '../../content/ui.ts'
import { monthLabel } from '../../state/months.ts'
import type { MonthOption } from '../../state/months.ts'
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

  // Left and Right step the month from the buttons too (the slider has them natively).
  const onKeyDown = (e: KeyboardEvent<HTMLDivElement>) => {
    if ((e.key !== 'ArrowLeft' && e.key !== 'ArrowRight') || (e.target as HTMLElement).tagName === 'INPUT') return
    e.preventDefault()
    manual(() => step(e.key === 'ArrowLeft' ? -1 : 1))
  }

  return (
    <div className="month-selector" role="group" aria-label="Month" onKeyDown={onKeyDown}>
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
        className="btn btn-secondary btn-icon"
        onClick={() => manual(() => step(-1))}
        disabled={!canBack}
        aria-label="Previous month"
      >
        ◀
      </button>
      <input
        type="range"
        min={0}
        max={Math.max(months.length - 1, 0)}
        value={Math.max(index, 0)}
        disabled={months.length === 0}
        onChange={(e) => manual(() => go(Number(e.target.value)))}
        aria-label="Month slider"
        aria-valuetext={current === null ? 'No month selected' : monthLabel(current)}
      />
      <button
        type="button"
        className="btn btn-secondary btn-icon"
        onClick={() => manual(() => step(1))}
        disabled={!canForward}
        aria-label="Next month"
      >
        ▶
      </button>
      <output aria-live={playing ? 'off' : 'polite'} className="month-value">
        {current === null
          ? outside
            ? `${monthLabel(value)} (no offline map)`
            : 'No month available'
          : monthLabel(current)}
        {current?.provisional === true && <span className="badge"> Provisional</span>}
      </output>
      {reduced && (
        <p id={noteId} className="month-note">
          {UI.REDUCED_MOTION_NOTE}
        </p>
      )}
    </div>
  )
}
