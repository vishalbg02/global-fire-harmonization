import { useId, useState } from 'react'
import type { Dispatch, ReactNode } from 'react'
import { SHEET_QUERY } from '../layout/sheet.ts'
import { useMediaQuery } from '../layout/useMediaQuery.ts'
import { DockIcon } from './DockIcon.tsx'
import * as UI from '../../content/ui.ts'
import type { MapViewAction, MapViewState } from '../../state/mapView.ts'
import { satDayRange } from '../map/gibs.ts'
import type { ImageryNoteKind } from '../map/gibs.ts'
import type { SelectMode } from '../map/MapModeSwitch.tsx'
import { SegmentedControl } from '../ui/SegmentedControl.tsx'
import { HelpTip } from '../help/HelpTip.tsx'
import './dock.css'

type Panel = 'select' | 'layers'

export interface DockProps {
  /** The area search (the first thing in the dock). */
  search: ReactNode
  view: MapViewState
  onView: Dispatch<MapViewAction>
  month: { year: number; month: number } | null
  /** The offline copy asks for no imagery: Satellite view is not offered. */
  offlineCopy: boolean
  /** The date Satellite view shows (YYYY-MM-DD), or null when it is off or not available. */
  satDate: string | null
  note: ImageryNoteKind | null
  today: string
  selectMode: SelectMode
  onSelectMode: (mode: SelectMode) => void
  drawDisabled: boolean
  /** The typed rectangle and polygon form. */
  customPanel: ReactNode
  /** Verdict / Activity and Raw / Harmonized. */
  layers: ReactNode
}

/**
 * The one control dock on the map (top left): the area search, the map shape, Satellite view with its date, and two
 * menus (how to select an area, what the map shows). Everything else on the map is the legend strip and the credit line.
 * On narrow screens (the bottom-sheet layout) it is one compact row: the search and four icon buttons, each named and
 * with a label that shows on hover, keyboard focus and long-press.
 */
export function Dock(p: DockProps) {
  const id = useId()
  const compact = useMediaQuery(SHEET_QUERY)
  const [panel, setPanel] = useState<Panel | null>(null)
  // While a drawing mode is on, its panel stays open so the hint is on screen.
  const shown: Panel | null = p.selectMode !== 'country' ? 'select' : panel
  const toggle = (which: Panel) => setPanel((cur) => (cur === which ? null : which))
  const range = p.month === null ? null : satDayRange(p.month.year, p.month.month, p.today)
  const satUnavailable = p.offlineCopy || range === null
  const satOn = p.view.satOn && !satUnavailable
  const days = range === null ? [] : Array.from({ length: range.last - range.first + 1 }, (_, i) => range.first + i)
  const dayValue = range === null ? p.view.satDay : Math.min(Math.max(p.view.satDay, range.first), range.last)
  const satHint = p.offlineCopy
    ? UI.IMAGERY_NOTE_OFFLINE
    : p.month === null
      ? UI.IMAGERY_SAT_UNAVAILABLE_NO_MONTH
      : range === null
        ? UI.IMAGERY_SAT_UNAVAILABLE_RANGE
        : UI.IMAGERY_SATELLITE_HINT
  return (
    <section
      className="dock"
      data-compact={compact}
      aria-label={UI.DOCK_LABEL}
      onKeyDown={(e) => {
        if (e.key === 'Escape' && panel !== null && p.selectMode === 'country') {
          const opener = document.getElementById(`${id}-${panel}-btn`)
          setPanel(null)
          opener?.focus()
        }
      }}
    >
      {compact ? (
        <div className="dock-bar">
          <div className="dock-search" data-tour="place">
            {p.search}
          </div>
          <div className="dock-icons">
            <DockIcon
              id={`${id}-select-btn`}
              label={UI.DOCK_SELECT}
              icon="select"
              aria-expanded={shown === 'select'}
              aria-controls={`${id}-select`}
              onClick={() => toggle('select')}
            />
            <DockIcon
              id={`${id}-layers-btn`}
              label={UI.DOCK_LAYERS}
              icon="layers"
              data-tour="raw"
              aria-expanded={shown === 'layers'}
              aria-controls={`${id}-layers`}
              onClick={() => toggle('layers')}
            />
            <DockIcon
              label={UI.IMAGERY_GLOBE}
              icon="globe"
              aria-pressed={p.view.shape === 'globe'}
              onClick={() => p.onView({ type: 'set-shape', shape: p.view.shape === 'globe' ? 'flat' : 'globe' })}
            />
            <DockIcon
              label={UI.IMAGERY_SATELLITE}
              icon="satellite"
              role="switch"
              aria-checked={satOn}
              aria-describedby={`${id}-sat-hint`}
              disabled={satUnavailable}
              onClick={() => p.onView({ type: 'toggle-sat' })}
            />
          </div>
          <span id={`${id}-sat-hint`} className="visually-hidden">
            {satHint}
          </span>
        </div>
      ) : (
        <>
        <div className="dock-search" data-tour="place">
          {p.search}
        </div>
        <div className="dock-row">
          <SegmentedControl<MapViewState['shape']>
            legend={UI.IMAGERY_SHAPE}
            name="map-shape"
            className="dock-shape"
            value={p.view.shape}
            onChange={(shape) => p.onView({ type: 'set-shape', shape })}
            options={[
              { value: 'flat', label: UI.IMAGERY_FLAT },
              { value: 'globe', label: UI.IMAGERY_GLOBE },
            ]}
          />
          <span className="dock-sat">
            <button
              type="button"
              role="switch"
              className="bare dock-switch"
              aria-checked={satOn}
              aria-describedby={`${id}-sat-hint`}
              disabled={satUnavailable}
              onClick={() => p.onView({ type: 'toggle-sat' })}
            >
              <span className="dock-switch-track" aria-hidden="true">
                <span className="dock-switch-thumb" />
              </span>
              {UI.IMAGERY_SATELLITE}
            </button>
            <HelpTip term="satellite-view" />
          </span>
          <span id={`${id}-sat-hint`} className="visually-hidden">
            {satHint}
          </span>
        </div>
        </>
      )}
      {satOn && p.satDate !== null && (
        <div className="dock-row dock-sat-row">
          <span className="dock-chip">{UI.SAT_CHIP(p.satDate)}</span>
          {compact && <HelpTip term="satellite-view" />}
          <label className="dock-day">
            {UI.DOCK_SAT_DAY}{' '}
            <select value={dayValue} onChange={(e) => p.onView({ type: 'set-sat-day', day: Number(e.target.value) })}>
              {days.map((d) => (
                <option key={d} value={d}>
                  {d}
                </option>
              ))}
            </select>
          </label>
        </div>
      )}
      {satUnavailable && !p.offlineCopy && p.view.satOn && <p className="dock-note">{satHint}</p>}
      {p.note !== null && (
        <p className="dock-note" role="status">
          {p.note === 'offline' ? UI.IMAGERY_NOTE_OFFLINE : UI.IMAGERY_NOTE_FAILED}
        </p>
      )}
      {!compact && (
      <div className="dock-row dock-menus">
        <button
          type="button"
          id={`${id}-select-btn`}
          className="bare dock-menu"
          aria-expanded={shown === 'select'}
          aria-controls={`${id}-select`}
          onClick={() => toggle('select')}
        >
          {UI.DOCK_SELECT}
          <span aria-hidden="true" className="dock-caret" />
        </button>
        <button
          type="button"
          id={`${id}-layers-btn`}
          className="bare dock-menu"
          data-tour="raw"
          aria-expanded={shown === 'layers'}
          aria-controls={`${id}-layers`}
          onClick={() => toggle('layers')}
        >
          {UI.DOCK_LAYERS}
          <span aria-hidden="true" className="dock-caret" />
        </button>
      </div>
      )}
      <div id={`${id}-select`} className="dock-panel" role="group" aria-label={UI.DOCK_SELECT_PANEL} hidden={shown !== 'select'}>
        <SegmentedControl<SelectMode>
          legend={UI.MAP_MODE_LABEL}
          name="select-mode"
          className="dock-seg-full"
          value={p.selectMode}
          onChange={p.onSelectMode}
          options={[
            { value: 'country', label: UI.MAP_MODES.country },
            { value: 'rectangle', label: UI.MAP_MODES.rectangle, disabled: p.drawDisabled },
            { value: 'polygon', label: UI.MAP_MODES.polygon, disabled: p.drawDisabled },
          ]}
        />
        <p className="dock-hint" role="status">
          {UI.MAP_MODE_HINT[p.selectMode]}
        </p>
        <details className="dock-typed">
          <summary>{UI.DOCK_TYPE_AREA}</summary>
          {p.customPanel}
        </details>
      </div>
      <div id={`${id}-layers`} className="dock-panel" role="group" aria-label={UI.DOCK_LAYERS_PANEL} hidden={shown !== 'layers'}>
        {p.layers}
      </div>
    </section>
  )
}
