import { useEffect, useState } from 'react'
import type { MapCell, MapLayer } from '../../api/contract.ts'
import { Legend, LegendKey } from './Legend.tsx'
import { LEGEND_COLOURS } from '../../content/earth.ts'
import { CellInfo } from './CellInfo.tsx'
import { legendForcedCollapsed } from './mapPlacement.ts'
import './mapOverlays.css'

// Map-folder constants of the overlays (T-071).
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

/**
 * The legend on the map: a compact strip at the bottom left that folds away (T-071, T-093). Folded, it keeps the verdict
 * colours visible as small swatches (named for screen readers); open, it adds the labels, the "Show all verdicts"
 * switch and the line that explains the low-zoom rule. Folded by default on narrow screens.
 */
export function MapLegend({
  layer,
  max,
  collapsed,
  cardPinned = false,
  showAll = false,
  onShowAll,
  ruleActive = false,
}: {
  layer: MapLayer
  max: number
  collapsed?: boolean
  cardPinned?: boolean
  showAll?: boolean
  onShowAll?: (on: boolean) => void
  ruleActive?: boolean
}) {
  const [open, setOpen] = useState<boolean>(!(collapsed ?? startsNarrow()))
  // While a card is pinned on a small screen the legend stays folded, so neither hides the other.
  const forced = legendForcedCollapsed(cardPinned, typeof window === 'undefined' ? 1000 : window.innerWidth)
  const hidden = forced || !open
  return (
    <div className="map-legend" data-open={!hidden}>
      <div className="map-legend-head">
        <button
          type="button"
          className="bare map-legend-toggle"
          aria-expanded={!hidden}
          aria-controls="map-legend-body"
          onClick={() => setOpen(hidden)}
        >
          <span className="map-legend-caret" aria-hidden="true" />
          {hidden ? LEGEND_SHOW : LEGEND_HIDE}
        </button>
        {hidden && <LegendKey layer={layer} max={max} label={LEGEND_COLOURS} />}
      </div>
      <div id="map-legend-body" hidden={hidden}>
        <Legend layer={layer} max={max} overlay showAll={showAll} onShowAll={onShowAll} ruleActive={ruleActive} />
      </div>
    </div>
  )
}

/**
 * While a month's cells load: a slim line along the top edge of the map (no spinner over the data), and the same news
 * in words for screen readers.
 */
export function MapLoading() {
  return (
    <div className="map-loading" role="status">
      <span className="map-progress" aria-hidden="true">
        <span className="map-progress-bar" />
      </span>
      <span className="visually-hidden">{LOADING_TEXT}</span>
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
  onPointerEnter,
}: {
  cell: MapCell
  layer: MapLayer
  onClose: () => void
  onPointerEnter?: () => void
}) {
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose()
    }
    document.addEventListener('keydown', onKey)
    return () => document.removeEventListener('keydown', onKey)
  }, [onClose])
  return (
    <section className="map-pinned" aria-label="Selected cell" onPointerEnter={onPointerEnter}>
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
