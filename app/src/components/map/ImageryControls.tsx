import { useState } from 'react'
import * as UI from '../../content/ui.ts'
import { GIBS_LINK, satDayRange } from './gibs.ts'
import type { ImageryNoteKind } from './gibs.ts'
import { NARROW_MAP_PX } from './mapOverlays.tsx'
import './imagery.css'

export type MapShape = 'flat' | 'globe'

function startsNarrow(): boolean {
  return typeof window !== 'undefined' && window.matchMedia(`(max-width: ${NARROW_MAP_PX}px)`).matches
}

export interface ImageryControlsProps {
  month: { year: number; month: number } | null
  /** The offline copy: no imagery is requested, so no Satellite view. */
  offlineCopy: boolean
  satOn: boolean
  onSatOn: (on: boolean) => void
  /** The day wished for; the map clamps it to the month. */
  satDay: number
  onSatDay: (day: number) => void
  /** The date being shown, or null when Satellite view is off or not available. */
  satDateShown: string | null
  shape: MapShape
  onShape: (shape: MapShape) => void
  /** False when the cells do not render correctly on the globe: the switch is then not offered. */
  globeOffered: boolean
  note: ImageryNoteKind | null
  today: string
}

/** The Map view panel (top left): Satellite view switch with a day picker, and the Flat / Globe choice. */
export function ImageryControls(p: ImageryControlsProps) {
  const [open, setOpen] = useState<boolean>(!startsNarrow())
  const range = p.month === null ? null : satDayRange(p.month.year, p.month.month, p.today)
  const satUnavailable = p.offlineCopy || range === null
  const days = range === null ? [] : Array.from({ length: range.last - range.first + 1 }, (_, i) => range.first + i)
  const dayValue = range === null ? p.satDay : Math.min(Math.max(p.satDay, range.first), range.last)
  return (
    <div className="map-imagery">
      <button
        type="button"
        className="map-imagery-toggle"
        aria-expanded={open}
        aria-controls="map-imagery-body"
        onClick={() => setOpen((o) => !o)}
      >
        {UI.IMAGERY_PANEL}
      </button>
      <div id="map-imagery-body" hidden={!open}>
        {!p.offlineCopy && (
          <div className="map-imagery-row">
            <button
              type="button"
              role="switch"
              aria-checked={p.satOn && !satUnavailable}
              aria-describedby="map-imagery-sat-hint"
              className="map-imagery-switch"
              disabled={satUnavailable}
              onClick={() => p.onSatOn(!p.satOn)}
            >
              <span className="map-imagery-track" aria-hidden="true">
                <span className="map-imagery-thumb" />
              </span>
              {UI.IMAGERY_SATELLITE}
            </button>
            <span id="map-imagery-sat-hint" className="map-imagery-hint">
              {p.month === null
                ? UI.IMAGERY_SAT_UNAVAILABLE_NO_MONTH
                : range === null
                  ? UI.IMAGERY_SAT_UNAVAILABLE_RANGE
                  : UI.IMAGERY_SATELLITE_HINT}
            </span>
          </div>
        )}
        {!satUnavailable && p.satOn && (
          <div className="map-imagery-row">
            <label>
              {UI.IMAGERY_DAY}{' '}
              <select value={dayValue} onChange={(e) => p.onSatDay(Number(e.target.value))}>
                {days.map((d) => (
                  <option key={d} value={d}>
                    {d}
                  </option>
                ))}
              </select>
            </label>
          </div>
        )}
        {p.globeOffered && (
          <fieldset className="map-imagery-shape">
            <legend>{UI.IMAGERY_SHAPE}</legend>
            {(['flat', 'globe'] as const).map((s) => (
              <label key={s}>
                <input type="radio" name="map-shape" value={s} checked={p.shape === s} onChange={() => p.onShape(s)} />{' '}
                {s === 'flat' ? UI.IMAGERY_FLAT : UI.IMAGERY_GLOBE}
              </label>
            ))}
          </fieldset>
        )}
      </div>
    </div>
  )
}

/** Credit, layer dates and the single failure note, along the bottom of the map. */
export function ImageryCredit({
  offlineCopy,
  satDateShown,
  note,
  basemapShown,
}: {
  offlineCopy: boolean
  satDateShown: string | null
  note: ImageryNoteKind | null
  basemapShown: boolean
}) {
  const [info, setInfo] = useState(false)
  return (
    <div className="map-credit">
      {note !== null && (
        <p className="map-imagery-note" role="status">
          {note === 'offline' ? UI.IMAGERY_NOTE_OFFLINE : UI.IMAGERY_NOTE_FAILED}
        </p>
      )}
      {!offlineCopy && (satDateShown !== null || basemapShown) && (
        <p className="map-credit-line">
          <strong>{satDateShown !== null ? UI.IMAGERY_SAT_DATE(satDateShown) : UI.IMAGERY_BASEMAP_DATE}</strong>
          {'. '}
          <a href={GIBS_LINK} target="_blank" rel="noreferrer" title={UI.IMAGERY_PRIVACY}>
            {UI.IMAGERY_CREDIT}
          </a>{' '}
          <button
            type="button"
            className="map-credit-info"
            aria-expanded={info}
            aria-controls="map-credit-privacy"
            aria-label={UI.IMAGERY_CREDIT_INFO}
            onClick={() => setInfo((v) => !v)}
          >
            {'i'}
          </button>
          <span id="map-credit-privacy" hidden={!info} className="map-credit-privacy">
            {' '}
            {UI.IMAGERY_PRIVACY} {UI.IMAGERY_CONTEXT}
          </span>
        </p>
      )}
    </div>
  )
}
