import { useEffect, useState } from 'react'
import type { MapCell, MapLayer } from '../../api/contract.ts'
import { Legend } from './Legend.tsx'
import { CellInfo } from './CellInfo.tsx'
import './mapOverlays.css'

// Map-folder constants (app/src/content/ui.ts does not exist yet; T-070 may move them there).
export const SCROLL_HINT = 'Use Ctrl + scroll to zoom the map'
export const SCROLL_HINT_MAC = 'Use ⌘ + scroll to zoom the map'
export const TOUCH_HINT = 'Use two fingers to move the map'
export const LOADING_TEXT = 'Loading map data…'
export const PINNED_CLOSE = 'Close cell details'
export const LEGEND_SHOW = 'Show legend'
export const LEGEND_HIDE = 'Hide legend'

/** On a narrow map the legend starts collapsed, so it does not cover the map. */
export const NARROW_MAP_PX = 700

function startsNarrow(): boolean {
  return typeof window !== 'undefined' && window.matchMedia(`(max-width: ${NARROW_MAP_PX}px)`).matches
}

/** The legend on the map (bottom left), collapsible; collapsed by default on narrow screens. */
export function MapLegend({ layer, max, collapsed }: { layer: MapLayer; max: number; collapsed?: boolean }) {
  const [hidden, setHidden] = useState<boolean>(collapsed ?? startsNarrow())
  return (
    <div className="map-legend">
      <button
        type="button"
        className="map-legend-toggle"
        aria-expanded={!hidden}
        aria-controls="map-legend-body"
        onClick={() => setHidden((h) => !h)}
      >
        {hidden ? LEGEND_SHOW : LEGEND_HIDE}
      </button>
      <div id="map-legend-body" hidden={hidden}>
        <Legend layer={layer} max={max} overlay />
      </div>
    </div>
  )
}

/** The visible, announced loading indicator on the map while a month's cells load. */
export function MapLoading() {
  return (
    <div className="map-loading" role="status">
      <span className="map-spinner" aria-hidden="true" />
      {LOADING_TEXT}
    </div>
  )
}

/** A small hint on the map: the page scrolls over it, and zooming needs Ctrl or Cmd. */
export function ScrollHint() {
  const mac = typeof navigator !== 'undefined' && /Mac|iPhone|iPad/.test(navigator.platform)
  return (
    <p className="map-hint">
      <span className="map-hint-pointer">{mac ? SCROLL_HINT_MAC : SCROLL_HINT}</span>
      <span className="map-hint-touch">{TOUCH_HINT}</span>
    </p>
  )
}

/**
 * The card of a clicked cell (T-071): stays on the map until it is closed (button or Esc) or
 * another cell is clicked. Shows the cell details with the full approved reason sentences.
 */
export function PinnedCellCard({
  cell,
  layer,
  onClose,
}: {
  cell: MapCell
  layer: MapLayer
  onClose: () => void
}) {
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose()
    }
    document.addEventListener('keydown', onKey)
    return () => document.removeEventListener('keydown', onKey)
  }, [onClose])
  return (
    <section className="map-pinned" aria-label="Selected cell">
      <div className="map-pinned-head">
        <h2>Selected cell</h2>
        <button type="button" onClick={onClose} aria-label={PINNED_CLOSE}>
          {'×'}
        </button>
      </div>
      <CellInfo cell={cell} layer={layer} fullReasons />
      <p className="map-pinned-foot">Press Esc to close.</p>
    </section>
  )
}
