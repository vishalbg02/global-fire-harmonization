import { useEffect, useId, useLayoutEffect, useMemo, useRef, useState } from 'react'
import type { KeyboardEvent, PointerEvent } from 'react'
import type { EntityMonth, Metadata } from '../../api/contract.ts'
import * as T from '../../content/timeline.ts'
import * as P from '../../content/monthPicker.ts'
import * as UI from '../../content/ui.ts'
import { monthKey, monthLabel, monthRange } from '../../state/months.ts'
import type { MonthOption } from '../../state/months.ts'
import { HelpTip } from '../help/HelpTip.tsx'
import { MonthPicker } from '../map/MonthPicker.tsx'
import { PLAY_INTERVAL_MS, useReducedMotion } from '../map/playback.ts'
import {
  fractionOf,
  halfMonth,
  joinMarks,
  lineSegments,
  monthAtFraction,
  neighbours,
  playStep,
  provisionalSpans,
  rangeOf,
  sliderKeyTarget,
  snapToAvailable,
  unavailableSpans,
  yearTicks,
} from './timeline.ts'
import type { YearMonth } from './timeline.ts'
import './timeline.css'

export interface TimelineProps {
  /** The months that have a map, in order (every month of the record, or a subset in an offline copy). */
  months: readonly MonthOption[]
  value: YearMonth | null
  onChange: (year: number, month: number) => void
  /** The metadata: the strip runs from its first to its latest month and shades its provisional months. */
  meta?: Metadata | null
  /** The selected area's monthly series (the world when no area is chosen), drawn faintly behind the strip. */
  series?: readonly EntityMonth[]
  /** Raw or harmonized: the line follows the view the map and the answer panel show. */
  source?: 'raw' | 'harmonized'
  /** The time-lapse state, owned by the caller so that the Space key and the Play button are one state. */
  playing?: boolean
  onPlayingChange?: (playing: boolean) => void
}

/** Wait this long after the last move of a drag before the map is asked for the month (the thumb follows at once). */
export const DRAG_COMMIT_MS = 120
const VIEW_W = 1000
const VIEW_H = 100
const DEFAULT_WIDTH = 960
const FLAG_HALF_PX = 64

const same = (a: YearMonth | null, b: YearMonth | null) => a !== null && b !== null && a.year === b.year && a.month === b.month

/** "September 2015" with the year in Mono. */
function MonthText({ m }: { m: YearMonth }) {
  const label = monthLabel(m)
  const cut = label.lastIndexOf(' ')
  return (
    <>
      {label.slice(0, cut)} <span className="tl-year">{label.slice(cut + 1)}</span>
    </>
  )
}

/**
 * The timeline scrubber (zone C, T-093): a slim strip over the whole record with year ticks, the selected area's monthly
 * values drawn faintly behind it (with gaps where a value is missing), provisional months shaded, the VIIRS joins marked,
 * and the current month as a vermillion thumb with its name. The strip is an ARIA slider (arrows a month, Page Up and Page
 * Down a year, Home and End); click or drag on it to scrub. Play / Pause, previous and next month, and "Choose a month"
 * (the T-087 picker) sit above it.
 */
export function Timeline({ months, value, onChange, meta = null, series, source = 'harmonized', playing: playingProp, onPlayingChange }: TimelineProps) {
  const ids = useId()
  const hintId = `${ids}-hint`
  const lineId = `${ids}-line`
  const joinsId = `${ids}-joins`
  const noteId = `${ids}-note`
  const pickerId = `${ids}-picker`

  // The full record (the strip's extent) and its provisional months; the map months when the metadata is not there.
  const record = useMemo(
    () => (meta === null ? months : monthRange(meta.first_month, meta.latest_month, meta.provisional_months)),
    [meta, months],
  )
  const range = useMemo(() => rangeOf(record), [record])
  const provisional = useMemo(
    () => meta?.provisional_months ?? record.filter((m) => m.provisional).map((m) => monthKey(m.year, m.month)),
    [meta, record],
  )

  const index = value === null ? -1 : months.findIndex((m) => same(m, value))
  const outside = index < 0 && value !== null && months.length > 0
  const near = outside ? neighbours(months, value) : { before: null, after: null }
  const canBack = outside ? near.before !== null : index > 0
  const canForward = outside ? near.after !== null : index >= 0 && index < months.length - 1

  // ---- The time-lapse (controlled when the caller passes `playing`) ----
  const [ownPlaying, setOwnPlaying] = useState(false)
  const playing = playingProp ?? ownPlaying
  const reduced = useReducedMotion()
  const latest = useRef({ onChange, onPlayingChange, months })
  useEffect(() => {
    latest.current = { onChange, onPlayingChange, months }
  })
  const setPlaying = (next: boolean) => {
    if (onPlayingChange !== undefined) onPlayingChange(next)
    else setOwnPlaying(next)
  }
  const setPlayingRef = useRef(setPlaying)
  useEffect(() => {
    setPlayingRef.current = setPlaying
  })
  const wasPlaying = useRef(false)
  useEffect(() => {
    const justStarted = playing && !wasPlaying.current
    wasPlaying.current = playing
    const step = playStep({ playing, justStarted, reduced, index, count: months.length })
    const show = (i: number) => {
      const m = latest.current.months[i]
      if (m !== undefined) latest.current.onChange(m.year, m.month)
    }
    if (step.type === 'stop') setPlayingRef.current(false)
    else if (step.type === 'go') show(step.index)
    else if (step.type === 'wait') {
      const timer = setTimeout(() => show(step.next), PLAY_INTERVAL_MS)
      return () => clearTimeout(timer)
    }
  }, [playing, reduced, index, months])
  const pause = () => {
    if (playing) setPlaying(false)
  }

  // ---- Scrubbing ----
  const stripRef = useRef<HTMLDivElement>(null)
  const [width, setWidth] = useState(0)
  useLayoutEffect(() => {
    const el = stripRef.current
    if (el === null) return
    setWidth(el.clientWidth)
    if (typeof ResizeObserver === 'undefined') return
    const ro = new ResizeObserver(() => setWidth(el.clientWidth))
    ro.observe(el)
    return () => ro.disconnect()
  }, [])
  const w = width > 0 ? width : DEFAULT_WIDTH
  const [preview, setPreview] = useState<YearMonth | null>(null)
  const [hover, setHover] = useState<YearMonth | null>(null)
  const dragging = useRef(false)
  const commitTimer = useRef<ReturnType<typeof setTimeout> | null>(null)
  const pending = useRef<YearMonth | null>(null)
  useEffect(() => () => {
    if (commitTimer.current !== null) clearTimeout(commitTimer.current)
  }, [])

  const commit = (m: YearMonth | null) => {
    if (commitTimer.current !== null) clearTimeout(commitTimer.current)
    commitTimer.current = null
    if (m !== null && !same(m, value)) onChange(m.year, m.month)
  }
  const monthAtPointer = (e: PointerEvent<HTMLDivElement>): YearMonth | null => {
    if (range === null) return null
    const rect = e.currentTarget.getBoundingClientRect()
    return rect.width > 0 ? monthAtFraction(range, (e.clientX - rect.left) / rect.width) : null
  }
  const scrubTo = (e: PointerEvent<HTMLDivElement>) => {
    const at = monthAtPointer(e)
    const snapped = at === null ? null : snapToAvailable(months, at)
    if (snapped === null || same(snapped, pending.current)) return
    pending.current = snapped
    setPreview(snapped)
    if (commitTimer.current !== null) clearTimeout(commitTimer.current)
    commitTimer.current = setTimeout(() => commit(snapped), DRAG_COMMIT_MS)
  }
  const onPointerDown = (e: PointerEvent<HTMLDivElement>) => {
    if (e.button !== 0 || months.length === 0) return
    try {
      e.currentTarget.setPointerCapture(e.pointerId)
    } catch {
      // No capture for this pointer (an old browser or a synthetic event): the drag still works while over the strip.
    }
    e.currentTarget.focus({ preventScroll: true })
    pause()
    dragging.current = true
    pending.current = null
    setHover(null)
    scrubTo(e)
  }
  const onPointerMove = (e: PointerEvent<HTMLDivElement>) => {
    if (dragging.current) scrubTo(e)
    else if (e.pointerType === 'mouse') setHover(monthAtPointer(e))
  }
  const endDrag = () => {
    if (!dragging.current) return
    dragging.current = false
    commit(pending.current)
    pending.current = null
    setPreview(null)
  }

  // ---- Keys on the slider ----
  const onKeyDown = (e: KeyboardEvent<HTMLDivElement>) => {
    if (!['ArrowLeft', 'ArrowRight', 'ArrowUp', 'ArrowDown', 'PageUp', 'PageDown', 'Home', 'End'].includes(e.key)) return
    // The slider owns these keys while it has the focus (the page-wide shortcuts must not move the month a second time).
    e.preventDefault()
    e.stopPropagation()
    const to = sliderKeyTarget(months, value, e.key)
    if (to === null) return
    pause()
    onChange(to.year, to.month)
  }

  // ---- Buttons ----
  const step = (direction: -1 | 1) => {
    pause()
    const to = outside ? (direction < 0 ? near.before : near.after) : (months[index + direction] ?? null)
    if (to !== null) onChange(to.year, to.month)
  }
  const togglePlay = () => {
    if (playing) setPlaying(false)
    else if (months.length > 0 && !reduced) setPlaying(true)
  }

  // ---- The picker ----
  const [pickerOpen, setPickerOpen] = useState(false)
  const rootRef = useRef<HTMLDivElement>(null)
  const triggerRef = useRef<HTMLButtonElement>(null)
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

  // ---- Geometry ----
  const shown = preview ?? value
  const ticks = useMemo(() => (range === null ? [] : yearTicks(range, w)), [range, w])
  const provSpans = useMemo(() => (range === null ? [] : provisionalSpans(range, provisional)), [range, provisional])
  const missingSpans = useMemo(() => (range === null ? [] : unavailableSpans(range, months)), [range, months])
  const joins = useMemo(() => (range === null ? [] : joinMarks(range)), [range])
  const field = source === 'raw' ? 'raw_combined_cell_days' : 'estimate'
  const segments = useMemo(() => (range === null ? [] : lineSegments(range, series, field)), [range, series, field])
  const narrow = w < 640
  const isProvisional = (m: YearMonth | null) => m !== null && provisional.includes(monthKey(m.year, m.month))
  const hasMap = (m: YearMonth | null) => m !== null && months.some((x) => same(x, m))
  const shownF = range !== null && shown !== null ? fractionOf(range, shown) : null
  const hoverF = range !== null && hover !== null ? fractionOf(range, hover) : null
  const flagAlign = (f: number) => (f * w < FLAG_HALF_PX ? 'start' : (1 - f) * w < FLAG_HALF_PX ? 'end' : 'middle')
  const lineText = series === undefined ? T.LINE_LOADING : source === 'raw' ? T.LINE_RAW : T.LINE_HARMONIZED
  const valueText = T.sliderValueText(shown, { provisional: isProvisional(shown), noMap: shown !== null && months.length > 0 && !hasMap(shown) })
  const sliderNow = index >= 0 ? index : Math.max(0, near.before === null ? 0 : months.findIndex((m) => same(m, near.before)))
  const h = range === null ? 0 : halfMonth(range) * VIEW_W
  const y = (v: number) => VIEW_H - 4 - v * (VIEW_H - 12)

  return (
    <div className="timeline" ref={rootRef}>
      <div className="tl-controls">
        <button
          type="button"
          className="btn btn-secondary tl-play"
          onClick={togglePlay}
          disabled={months.length === 0}
          aria-disabled={reduced || undefined}
          aria-pressed={playing}
          aria-label={playing ? UI.PAUSE_LABEL : UI.PLAY_LABEL}
          aria-describedby={reduced ? noteId : undefined}
        >
          <span aria-hidden="true" className="tl-play-icon">
            {playing ? '❚❚' : '▶'}
          </span>
          <span className="tl-play-text">{playing ? UI.PAUSE : UI.PLAY}</span>
        </button>
        <button type="button" className="btn btn-secondary btn-icon tl-step" onClick={() => step(-1)} disabled={!canBack} aria-label={T.PREVIOUS_MONTH} title={T.PREVIOUS_MONTH}>
          <span aria-hidden="true">‹</span>
        </button>
        <button type="button" className="btn btn-secondary btn-icon tl-step" onClick={() => step(1)} disabled={!canForward} aria-label={T.NEXT_MONTH} title={T.NEXT_MONTH}>
          <span aria-hidden="true">›</span>
        </button>
        {reduced ? (
          <p id={noteId} className="tl-caption tl-note">
            {UI.REDUCED_MOTION_NOTE}
          </p>
        ) : (
          <p id={lineId} className="tl-caption">
            {lineText}
          </p>
        )}
        <span className="tl-key">
          <span className="tl-key-swatch" aria-hidden="true" />
          <span className="tl-key-text" title={T.PROVISIONAL_KEY_LABEL}>
            {T.PROVISIONAL}
          </span>
          <HelpTip term="provisional" />
        </span>
        <button
          type="button"
          ref={triggerRef}
          className="btn btn-secondary month-picker-trigger"
          aria-haspopup="dialog"
          aria-expanded={pickerOpen}
          aria-controls={pickerOpen ? pickerId : undefined}
          disabled={months.length === 0}
          onClick={() => {
            pause()
            setPickerOpen((open) => !open)
          }}
        >
          {P.PICKER_OPEN_LABEL} <span aria-hidden="true">▾</span>
        </button>
        {pickerOpen && (
          <div id={pickerId} className="month-picker-anchor">
            <MonthPicker
              months={months}
              value={value}
              onChoose={(year, month) => {
                pause()
                onChange(year, month)
                closePicker()
              }}
              onClose={closePicker}
            />
          </div>
        )}
      </div>

      <div
        ref={stripRef}
        className={`tl-strip${months.length === 0 ? ' is-empty' : ''}`}
        role="slider"
        tabIndex={months.length === 0 ? -1 : 0}
        aria-label={T.SLIDER_LABEL}
        aria-valuemin={0}
        aria-valuemax={Math.max(months.length - 1, 0)}
        aria-valuenow={sliderNow}
        aria-valuetext={valueText}
        aria-disabled={months.length === 0 || undefined}
        aria-describedby={`${hintId} ${reduced ? '' : lineId} ${joinsId}`.replace(/\s+/g, ' ').trim()}
        onKeyDown={onKeyDown}
        onPointerDown={onPointerDown}
        onPointerMove={onPointerMove}
        onPointerUp={endDrag}
        onPointerCancel={endDrag}
        onLostPointerCapture={endDrag}
        onPointerLeave={() => setHover(null)}
      >
        <div className="tl-flags" aria-hidden="true">
          {shown !== null && shownF !== null && (
            <span className={`tl-flag is-${flagAlign(shownF)}`} style={{ left: `${shownF * 100}%` }}>
              <MonthText m={shown} />
              {isProvisional(shown) && <span className="tl-flag-prov"> · {T.PROVISIONAL}</span>}
            </span>
          )}
          {hover !== null && hoverF !== null && !same(hover, shown) && (
            <span className={`tl-flag tl-hover-flag is-${flagAlign(hoverF)}`} style={{ left: `${hoverF * 100}%` }}>
              <MonthText m={hover} />
              {months.length > 0 && !hasMap(hover) && <span> {T.NO_MAP_SUFFIX}</span>}
            </span>
          )}
        </div>
        <div className="tl-track" aria-hidden="true">
          {missingSpans.map((s) => (
            <span key={`m${s.from}`} className="tl-span tl-missing" style={{ left: `${s.from * 100}%`, width: `${(s.to - s.from) * 100}%` }} />
          ))}
          {provSpans.map((s) => (
            <span key={`p${s.from}`} className="tl-span tl-prov" style={{ left: `${s.from * 100}%`, width: `${(s.to - s.from) * 100}%` }} />
          ))}
          <svg className="tl-line" viewBox={`0 0 ${VIEW_W} ${VIEW_H}`} preserveAspectRatio="none" focusable="false">
            {segments.map((seg) =>
              seg.length === 1 ? (
                <line key={seg[0]!.f} x1={seg[0]!.f * VIEW_W - h} x2={seg[0]!.f * VIEW_W + h} y1={y(seg[0]!.h)} y2={y(seg[0]!.h)} />
              ) : (
                <polyline key={seg[0]!.f} points={seg.map((p) => `${(p.f * VIEW_W).toFixed(2)},${y(p.h).toFixed(2)}`).join(' ')} />
              ),
            )}
          </svg>
          {joins.map((j) => (
            <span key={j.label} className="tl-join" style={{ left: `${j.f * 100}%` }}>
              <span className="tl-join-label">{narrow ? j.short : j.label}</span>
            </span>
          ))}
          {hoverF !== null && <span className="tl-hover" style={{ left: `${hoverF * 100}%` }} />}
          {shownF !== null && <span className="tl-thumb" style={{ left: `${shownF * 100}%` }} />}
        </div>
        <div className="tl-ticks" aria-hidden="true">
          {ticks.map((t) => (
            <span key={t.year} className={t.labelled ? 'tl-tick is-labelled' : 'tl-tick'} style={{ left: `${t.f * 100}%` }}>
              {t.labelled && <span className={`tl-tick-label is-${t.align}`}>{t.year}</span>}
            </span>
          ))}
        </div>
      </div>

      <span id={hintId} className="visually-hidden">
        {P.SLIDER_HINT}
      </span>
      <span id={joinsId} className="visually-hidden">
        {T.joinsSummary(joins)}
      </span>
      <output className="visually-hidden" aria-live={playing ? 'off' : 'polite'}>
        {value === null || months.length === 0
          ? T.NO_MONTH
          : outside
            ? `${monthLabel(value)} ${T.NO_MAP_SUFFIX}`
            : `${monthLabel(value)}${isProvisional(value) ? ` ${T.PROVISIONAL}` : ''}`}
      </output>
    </div>
  )
}
