import { useState } from 'react'
import type { FormEvent } from 'react'
import type { Bbox } from '../../api/contract.ts'
import { STATIC_CUSTOM_MESSAGE, useStaticManifest } from '../../api/staticData.ts'
import { parseBboxFields } from '../../state/bbox.ts'
import {
  POLYGON_DRAW_HINT,
  POLYGON_NOTE,
  parsePolygonText,
  polygonAnnouncement,
  ringToLines,
} from '../../state/polygon.ts'
import type { Ring } from '../../state/polygon.ts'
import type { BboxFields } from '../../state/bbox.ts'

export const GRID_NOTE = 'Custom areas are approximated by the grid cells whose centres fall inside the box.'

/** The polygon route of the form (T-044). */
export interface PolygonControls {
  onSubmit: (ring: Ring) => void
  drawing: boolean
  onToggleDrawing: () => void
  /** Grid cells of the current polygon (`n_cells` of its series), null until known. */
  cells: number | null
  /** A polygon drawn on the map that has not been accepted, so the text box shows it and its reason. */
  draft?: { ring: Ring; error: string | null; seq: number } | null
  /** Set by the picker from the current area and the draft. */
  initial?: Ring | null
  drawError?: string | null
  active?: boolean
}

interface Props {
  polygon?: PolygonControls
  /** The current custom box, to fill the fields. The form is re-created when it changes. */
  initial: Bbox | null
  onSubmit: (bbox: Bbox) => void
  drawing: boolean
  onToggleDrawing: () => void
  /** The server's message for the current custom area (for example a 422 or a 503). */
  serverMessage: string | null
  loading: boolean
}

const FIELDS: readonly { key: keyof BboxFields; label: string; hint: string }[] = [
  { key: 'west', label: 'West', hint: 'longitude, -180 to 180' },
  { key: 'south', label: 'South', hint: 'latitude, -90 to 90' },
  { key: 'east', label: 'East', hint: 'longitude, -180 to 180' },
  { key: 'north', label: 'North', hint: 'latitude, -90 to 90' },
]

/**
 * A custom rectangle by typed west, south, east and north (degrees, WGS84). The typed form is
 * the keyboard route to a custom area; drawing on the map is pointer-only.
 */
/** Shown while a custom area is computed; a new area can take several seconds (T-042). */
export const CUSTOM_COMPUTING =
  'Computing this area from the satellite records. A new area can take several seconds.'

export function CustomAreaForm({ initial, polygon, onSubmit, drawing, onToggleDrawing, serverMessage, loading }: Props) {
  // The offline copy has the preset views only (T-043): the form says so and cannot be submitted.
  const offline = useStaticManifest() !== null
  const [fields, setFields] = useState<BboxFields>({
    west: initial === null ? '' : String(initial[0]),
    south: initial === null ? '' : String(initial[1]),
    east: initial === null ? '' : String(initial[2]),
    north: initial === null ? '' : String(initial[3]),
  })
  const [error, setError] = useState<string | null>(null)
  const [polygonText, setPolygonText] = useState(polygon?.initial == null ? '' : ringToLines(polygon.initial))
  const [polygonError, setPolygonError] = useState<string | null>(null)

  const submitPolygon = (event: FormEvent) => {
    event.preventDefault()
    const check = parsePolygonText(polygonText)
    if (!check.ok) {
      setPolygonError(check.message)
      return
    }
    setPolygonError(null)
    polygon?.onSubmit(check.ring)
  }

  const submit = (event: FormEvent) => {
    event.preventDefault()
    const check = parseBboxFields(fields)
    if (!check.ok) {
      setError(check.message)
      return
    }
    setError(null)
    onSubmit(check.bbox)
  }

  return (
    <form aria-busy={loading} className="custom-area" onSubmit={submit} noValidate aria-labelledby="custom-area-title">
      <h3 id="custom-area-title">Custom area</h3>
      <div className="bbox-fields">
        {FIELDS.map((f) => (
          <label key={f.key}>
            {`${f.label} (degrees)`}
            <input
              type="text"
              inputMode="decimal"
              value={fields[f.key]}
              onChange={(e) => setFields({ ...fields, [f.key]: e.target.value })}
              aria-describedby="custom-area-hint"
              placeholder={f.hint}
            />
          </label>
        ))}
      </div>
      <p id="custom-area-hint" className="legend-note">
        Latitude and longitude in degrees (WGS84). West must be less than east, and south less than north.
      </p>
      <div className="custom-actions">
        <button type="submit" disabled={loading || offline}>
          Show custom area
        </button>
        <button type="button" onClick={onToggleDrawing} aria-pressed={drawing} disabled={offline}>
          {drawing ? 'Cancel drawing' : 'Draw on the map'}
        </button>
      </div>
      {offline && (
        <p className="form-error" role="status">
          {STATIC_CUSTOM_MESSAGE}
        </p>
      )}
      {loading && (
        <p className="custom-computing" role="status">
          {CUSTOM_COMPUTING}
        </p>
      )}
      {drawing && (
        <p className="legend-note" role="status">
          Click two opposite corners on the map. Drawing needs a pointer; use the fields above to
          enter a box with the keyboard.
        </p>
      )}
      {error !== null && (
        <p className="form-error" role="alert">
          {error}
        </p>
      )}
      {serverMessage !== null && <p className="form-error">{serverMessage}</p>}
      <p className="legend-note">{GRID_NOTE}</p>
      {polygon !== undefined && (
        <div className="custom-polygon" role="group" aria-labelledby="custom-polygon-title">
          <h4 id="custom-polygon-title">Custom polygon</h4>
          <label>
            Corner points, one per line: longitude, latitude (degrees)
            <textarea
              rows={6}
              value={polygonText}
              onChange={(e) => setPolygonText(e.target.value)}
              aria-describedby="custom-polygon-note"
              placeholder={'100, 0\n101, 0\n101, 1'}
              spellCheck={false}
              disabled={offline}
            />
          </label>
          <div className="custom-actions">
            <button type="button" onClick={submitPolygon} disabled={loading || offline}>
              Show polygon
            </button>
            <button type="button" onClick={polygon.onToggleDrawing} aria-pressed={polygon.drawing} disabled={offline}>
              {polygon.drawing ? 'Cancel drawing' : 'Draw a polygon on the map'}
            </button>
          </div>
          {polygon.drawing && (
            <p className="legend-note" role="status">
              {POLYGON_DRAW_HINT}
            </p>
          )}
          {polygon.active === true && polygon.initial != null && (
            <p className="polygon-announcement" role="status">
              {polygonAnnouncement(polygon.initial.length, polygon.cells)}
            </p>
          )}
          {(polygonError ?? polygon.drawError ?? null) !== null && (
            <p className="form-error" role="alert">
              {polygonError ?? polygon.drawError}
            </p>
          )}
          <p id="custom-polygon-note" className="legend-note">
            {POLYGON_NOTE}
          </p>
        </div>
      )}
    </form>
  )
}
