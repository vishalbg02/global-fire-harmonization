import { useCallback, useEffect, useMemo, useReducer, useRef, useState } from 'react'
import * as maplibregl from 'maplibre-gl'
import type { MapGeoJSONFeature, MapMouseEvent, StyleSpecification } from 'maplibre-gl'
import 'maplibre-gl/dist/maplibre-gl.css'
import maplibreWorkerUrl from 'maplibre-gl/dist/maplibre-gl-worker.mjs?worker&url'
import { MapLibreOverlay } from '@deck.gl/maplibre'
import { GeoJsonLayer, PolygonLayer, TextLayer } from '@deck.gl/layers'
import { TerraDraw, TerraDrawPolygonMode, TerraDrawRectangleMode } from 'terra-draw'
import { TerraDrawMapLibreGLAdapter } from 'terra-draw-maplibre-gl-adapter'
import type { Bbox, MapCell, MapLayer } from '../../api/contract.ts'
import { bboxFromRing } from '../../state/bbox.ts'
import { pinnedReducer } from '../../state/pinnedCell.ts'
import { tooltipCellId } from './mapPlacement.ts'
import { openRing } from '../../state/polygon.ts'
import type { Ring } from '../../state/polygon.ts'
import { WORLD_BBOX } from '../../state/selection.ts'
import type { FitRequest } from '../../state/selection.ts'
import { VERDICT_PRESENTATION } from '../../content/verdicts.ts'
import { CellInfo } from './CellInfo.tsx'
import { countryIso3, countryName } from './countries.ts'
import { CELL_STROKE_ALPHA, cellFillColor, cellStrokeWidth, needsOutline, sharedMax } from './scale.ts'
import {
  MapLegend,
  MapLoading,
  PinnedCellCard,
  SCROLL_HINT,
  SCROLL_HINT_MAC,
  ScrollHint,
  TOUCH_HINT,
} from './mapOverlays.tsx'

// MapLibre 6 runs in a module worker. Bundlers do not emit it automatically, so register
// it through Vite (works in both the dev server and the production build).
maplibregl.setWorkerUrl(maplibreWorkerUrl)

// A plain background: no external tiles, so no key and it works offline.
const STYLE: StyleSpecification = {
  version: 8,
  sources: {},
  layers: [{ id: 'background', type: 'background', paint: { 'background-color': '#dbe7f1' } }],
}

const COUNTRIES_URL = `${import.meta.env.BASE_URL}geo/ne_admin_0_countries_india_pov.geojson`

const INITIAL_ZOOM = 1.2
/** From this zoom a 0.5 degree cell is about 16 px wide, enough for its 13 px verdict icon. */
export const ICON_MIN_ZOOM = 4.5

interface Props {
  cells: readonly MapCell[] | null
  layer: MapLayer
  selectedCellId: string | null
  selectedCountryIso3: string | null
  onSelectCell: (cell: MapCell) => void
  onSelectCountry: (iso3: string, name: string) => void
  /** Fit the map to this box whenever the object changes (an area chosen in the picker). */
  fit: FitRequest | null
  /** The selected custom rectangle, outlined on the map. */
  customBbox: Bbox | null
  /** The selected custom polygon, outlined instead of its bounding box (T-044). */
  customRing?: Ring | null
  /** While true, the user draws a rectangle with two clicks. */
  drawing: boolean
  onDrawn: (bbox: Bbox) => void
  /** While true, the user draws a polygon: a click per corner, double-click or Enter to finish. */
  polygonDrawing?: boolean
  /** The drawn ring, open (first point not repeated); the app validates it like a typed one. */
  onDrawnPolygon?: (ring: number[][]) => void
  /** ISO3 codes of the countries listed in the anomaly rankings, to outline (T-040). */
  anomalyOutlines: { above: readonly string[]; below: readonly string[] }
  /** The country under the pointer (null when none): the app shows its name and verdict (T-070). */
  onHoverCountry?: (country: { iso3: string; name: string } | null) => void
  /** True while the month's cells are loading: shows the loading indicator on the map (T-071). */
  loading?: boolean
}

const CUSTOM_SOURCE = 'custom-area'

function boxFeature(bbox: Bbox) {
  const [w, s, e, n] = bbox
  return {
    type: 'Feature' as const,
    properties: {},
    geometry: { type: 'Polygon' as const, coordinates: [[[w, s], [e, s], [e, n], [w, n], [w, s]]] },
  }
}

function ringFeature(ring: Ring) {
  return {
    type: 'Feature' as const,
    properties: {},
    geometry: { type: 'Polygon' as const, coordinates: [[...ring, ring[0]]] },
  }
}

function prefersReducedMotion(): boolean {
  return typeof window !== 'undefined' && window.matchMedia('(prefers-reduced-motion: reduce)').matches
}

export function MapView({
  cells,
  layer,
  selectedCellId,
  selectedCountryIso3,
  onSelectCell,
  onSelectCountry,
  fit,
  customBbox,
  customRing = null,
  drawing,
  onDrawn,
  polygonDrawing = false,
  onDrawnPolygon,
  anomalyOutlines,
  onHoverCountry,
  loading = false,
}: Props) {
  const container = useRef<HTMLDivElement>(null)
  const mapRef = useRef<maplibregl.Map | null>(null)
  const overlayRef = useRef<MapLibreOverlay | null>(null)
  const loaded = useRef(false)
  const wrap = useRef<HTMLDivElement>(null)
  // Zoom of the map: the verdict icons are drawn only when a cell is big enough to hold one.
  const [zoom, setZoom] = useState(INITIAL_ZOOM)
  // The outline of the country under the pointer, drawn above the cells (T-070).
  const [hoverOutline, setHoverOutline] = useState<unknown>(null)
  const countryShapes = useRef<Map<string, unknown> | null>(null)
  const [hover, setHover] = useState<{ cell: MapCell; x: number; y: number; w: number; h: number } | null>(null)
  const callbacks = useRef({ onSelectCell, onSelectCountry, onDrawn, onDrawnPolygon, onHoverCountry })
  // The cell whose card is pinned on the map: until closed, Esc, or another cell is clicked (T-071).
  const [pinned, pinDispatch] = useReducer(pinnedReducer, null)
  useEffect(() => pinDispatch({ type: 'selection', selectedCellId }), [selectedCellId])
  const closePinned = useCallback(() => pinDispatch({ type: 'dismiss' }), [])
  const pinnedCell = useMemo(
    () => (pinned === null || cells === null ? null : (cells.find((c) => c.cell_id === pinned) ?? null)),
    [pinned, cells],
  )
  const legendMax = useMemo(() => (cells === null ? 0 : sharedMax(cells)), [cells])
  // Clicks are ignored while drawing, and for a moment after a rectangle is finished, so that
  // the click that ends the drawing does not also select a country or a cell.
  const ignoreClicksUntil = useRef(0)
  const drawingRef = useRef(drawing)
  useEffect(() => {
    callbacks.current = { onSelectCell, onSelectCountry, onDrawn, onDrawnPolygon, onHoverCountry }
    drawingRef.current = drawing || polygonDrawing
  })
  const clicksIgnored = () => drawingRef.current || Date.now() < ignoreClicksUntil.current

  useEffect(() => {
    if (container.current === null) return
    const map = new maplibregl.Map({
      container: container.current,
      style: STYLE,
      // Start on the same world view the World button gives: about 60S to 80N.
      bounds: [
        [WORLD_BBOX[0], WORLD_BBOX[1]],
        [WORLD_BBOX[2], WORLD_BBOX[3]],
      ],
      fitBoundsOptions: { padding: 30 },
      renderWorldCopies: false,
      attributionControl: false,
      // The page scrolls over the map; zoom needs Ctrl or Cmd + scroll (or the buttons or keys).
      // Touch: one finger scrolls the page, two move the map. The messages are MapLibre's own.
      cooperativeGestures: true,
      locale: {
        'CooperativeGesturesHandler.WindowsHelpText': SCROLL_HINT,
        'CooperativeGesturesHandler.MacHelpText': SCROLL_HINT_MAC,
        'CooperativeGesturesHandler.MobileHelpText': TOUCH_HINT,
      },
    })
    map.addControl(new maplibregl.NavigationControl({ showCompass: false }), 'top-right')
    // The focusable map canvas gets a name and its keyboard keys (MapLibre: arrows pan, plus and minus zoom).
    map.getCanvas().setAttribute(
      'aria-label',
      'Map canvas. Use the arrow keys to pan and the plus and minus keys to zoom. Choose an area with the search, the typed box or the lists.',
    )
    const overlay = new MapLibreOverlay({ interleaved: false, layers: [] })
    map.addControl(overlay)
    mapRef.current = map
    overlayRef.current = overlay
    setZoom(map.getZoom())
    map.on('zoomend', () => setZoom(map.getZoom()))

    // The same file the map layer reads (cached by the browser): the shapes for the hover outline.
    void fetch(COUNTRIES_URL)
      .then((r) => r.json())
      .then((collection: { features: { properties: Record<string, unknown> }[] }) => {
        const shapes = new Map<string, unknown>()
        for (const f of collection.features) {
          const iso3 = countryIso3(f.properties)
          if (iso3 !== null) shapes.set(iso3, f)
        }
        countryShapes.current = shapes
      })
      .catch(() => {
        countryShapes.current = null
      })

    map.on('load', () => {
      map.addSource('countries', { type: 'geojson', data: COUNTRIES_URL })
      map.addLayer({ id: 'countries-fill', type: 'fill', source: 'countries', paint: { 'fill-color': '#f7f7f2', 'fill-opacity': 1 } })
      map.addLayer({ id: 'countries-line', type: 'line', source: 'countries', paint: { 'line-color': '#8a8f98', 'line-width': 0.6 } })
      // Countries in the anomaly rankings (T-040): vermillion solid for above, dashed blue for
      // below, so the two differ by line style as well as colour. Added before the selection
      // outline so the selected country stays on top.
      map.addLayer({
        id: 'anomalies-above',
        type: 'line',
        source: 'countries',
        paint: { 'line-color': '#D55E00', 'line-width': 2 },
        filter: ['in', ['get', 'ISO_A3_EH'], ['literal', []]],
      })
      map.addLayer({
        id: 'anomalies-below',
        type: 'line',
        source: 'countries',
        paint: { 'line-color': '#0072B2', 'line-width': 2, 'line-dasharray': [2, 1.5] },
        filter: ['in', ['get', 'ISO_A3_EH'], ['literal', []]],
      })
      // Hover: the outline of the country under the pointer (T-070).
      map.addLayer({
        id: 'countries-hover',
        type: 'line',
        source: 'countries',
        paint: { 'line-color': '#14181f', 'line-width': 2 },
        filter: ['==', ['get', 'ISO_A3_EH'], ''],
      })
      map.addLayer({
        id: 'countries-selected',
        type: 'line',
        source: 'countries',
        paint: { 'line-color': '#0050c8', 'line-width': 2.5 },
        filter: ['==', ['get', 'ISO_A3_EH'], ''],
      })
      map.addSource(CUSTOM_SOURCE, { type: 'geojson', data: { type: 'FeatureCollection', features: [] } })
      map.addLayer({ id: 'custom-area-fill', type: 'fill', source: CUSTOM_SOURCE, paint: { 'fill-color': '#0050c8', 'fill-opacity': 0.08 } })
      map.addLayer({
        id: 'custom-area-line',
        type: 'line',
        source: CUSTOM_SOURCE,
        paint: { 'line-color': '#0050c8', 'line-width': 2.5, 'line-dasharray': [3, 2] },
      })
      loaded.current = true
    })
    map.on('click', 'countries-fill', (e: MapMouseEvent & { features?: MapGeoJSONFeature[] }) => {
      if (clicksIgnored()) return
      const props = e.features?.[0]?.properties
      const iso3 = countryIso3(props)
      if (iso3 !== null) callbacks.current.onSelectCountry(iso3, countryName(props))
    })
    map.on('mouseenter', 'countries-fill', () => (map.getCanvas().style.cursor = drawingRef.current ? 'crosshair' : 'pointer'))
    let hoverIso3: string | null = null
    const setHover = (iso3: string | null, name = '') => {
      if (iso3 === hoverIso3) return
      hoverIso3 = iso3
      if (loaded.current) map.setFilter('countries-hover', ['==', ['get', 'ISO_A3_EH'], iso3 ?? ''])
      callbacks.current.onHoverCountry?.(iso3 === null ? null : { iso3, name })
      setHoverOutline(iso3 === null ? null : (countryShapes.current?.get(iso3) ?? null))
    }
    map.on('mousemove', 'countries-fill', (e: MapMouseEvent & { features?: MapGeoJSONFeature[] }) => {
      if (drawingRef.current) return setHover(null)
      const props = e.features?.[0]?.properties
      const iso3 = countryIso3(props)
      setHover(iso3, countryName(props))
    })
    map.on('mouseleave', 'countries-fill', () => {
      map.getCanvas().style.cursor = ''
      setHover(null)
    })

    return () => {
      loaded.current = false
      map.remove()
      mapRef.current = null
      overlayRef.current = null
    }
  }, [])

  useEffect(() => {
    const map = mapRef.current
    if (map === null) return
    const apply = () => map.setFilter('countries-selected', ['==', ['get', 'ISO_A3_EH'], selectedCountryIso3 ?? ''])
    if (loaded.current) apply()
    else map.once('load', apply)
  }, [selectedCountryIso3])

  // Outline the countries listed in the anomaly rankings.
  useEffect(() => {
    const map = mapRef.current
    if (map === null) return
    const apply = () => {
      map.setFilter('anomalies-above', ['in', ['get', 'ISO_A3_EH'], ['literal', [...anomalyOutlines.above]]])
      map.setFilter('anomalies-below', ['in', ['get', 'ISO_A3_EH'], ['literal', [...anomalyOutlines.below]]])
    }
    if (loaded.current) apply()
    else map.once('load', apply)
  }, [anomalyOutlines])

  // Outline the custom rectangle.
  useEffect(() => {
    const map = mapRef.current
    if (map === null) return
    const apply = () => {
      const source = map.getSource(CUSTOM_SOURCE) as maplibregl.GeoJSONSource | undefined
      source?.setData({ type: 'FeatureCollection', features: customRing !== null ? [ringFeature(customRing)] : customBbox === null ? [] : [boxFeature(customBbox)],
      })
    }
    if (loaded.current) apply()
    else map.once('load', apply)
  }, [customBbox, customRing])

  // Fit the map to an area chosen in the picker (no animation if the user prefers reduced motion).
  useEffect(() => {
    const map = mapRef.current
    if (map === null || fit === null) return
    const [w, s, e, n] = fit.bbox
    map.fitBounds(
      [
        [w, s],
        [e, n],
      ],
      { padding: 30, maxZoom: 6, animate: !prefersReducedMotion() },
    )
  }, [fit])

  // Draw a rectangle with two clicks (terra-draw and its MapLibre adapter, D-024).
  useEffect(() => {
    const map = mapRef.current
    if (map === null || !drawing) return
    let draw: TerraDraw | null = null
    const start = () => {
      draw = new TerraDraw({
        adapter: new TerraDrawMapLibreGLAdapter({ map }),
        modes: [new TerraDrawRectangleMode()],
      })
      draw.start()
      draw.setMode('rectangle')
      draw.on('finish', (id) => {
        const feature = draw?.getSnapshot().find((f) => f.id === id)
        const ring = feature?.geometry.type === 'Polygon' ? feature.geometry.coordinates[0] : null
        draw?.clear()
        ignoreClicksUntil.current = Date.now() + 400
        if (ring === null || ring === undefined) return
        const check = bboxFromRing(ring)
        if (check.ok) callbacks.current.onDrawn(check.bbox)
      })
    }
    if (loaded.current) start()
    else map.once('load', start)
    return () => {
      map.off('load', start)
      if (draw !== null) {
        draw.stop()
        draw = null
      }
    }
  }, [drawing])

  // Draw a polygon (TerraDrawPolygonMode): one click per corner; a double-click or Enter finishes,
  // Escape drops the polygon in progress. Double-click zoom is off meanwhile so it cannot zoom.
  useEffect(() => {
    const map = mapRef.current
    if (map === null || !polygonDrawing) return
    let draw: TerraDraw | null = null
    const start = () => {
      map.doubleClickZoom.disable()
      draw = new TerraDraw({
        adapter: new TerraDrawMapLibreGLAdapter({ map }),
        modes: [new TerraDrawPolygonMode({ keyEvents: { cancel: 'Escape', finish: 'Enter' } })],
      })
      draw.start()
      draw.setMode('polygon')
      draw.on('finish', (id) => {
        const feature = draw?.getSnapshot().find((f) => f.id === id)
        const ring = feature?.geometry.type === 'Polygon' ? feature.geometry.coordinates[0] : null
        draw?.clear()
        ignoreClicksUntil.current = Date.now() + 400
        if (ring === null || ring === undefined) return
        callbacks.current.onDrawnPolygon?.(openRing(ring))
      })
    }
    if (loaded.current) start()
    else map.once('load', start)
    return () => {
      map.off('load', start)
      map.doubleClickZoom.enable()
      if (draw !== null) {
        draw.stop()
        draw = null
      }
    }
  }, [polygonDrawing])

  useEffect(() => {
    const overlay = overlayRef.current
    if (overlay === null) return
    const outline =
      hoverOutline === null
        ? []
        : [
            new GeoJsonLayer({
              id: 'hover-outline',
              // eslint-disable-next-line @typescript-eslint/no-explicit-any -- one Natural Earth feature, read from the countries file
              data: hoverOutline as any,
              pickable: false,
              stroked: true,
              filled: false,
              getLineColor: [20, 24, 31, 255],
              getLineWidth: 3,
              lineWidthUnits: 'pixels',
            }),
          ]
    if (cells === null || cells.length === 0) {
      overlay.setProps({ layers: outline })
      return
    }
    const max = sharedMax(cells)
    const strokeWidth = cellStrokeWidth(zoom)
    const polygons = new PolygonLayer<MapCell>({
      id: 'cells',
      data: cells as MapCell[],
      pickable: true,
      stroked: true,
      filled: true,
      getPolygon: (c) => [
        [c.lon_min, c.lat_min],
        [c.lon_max, c.lat_min],
        [c.lon_max, c.lat_max],
        [c.lon_min, c.lat_max],
      ],
      getFillColor: (c) => [...cellFillColor(c, layer, max)],
      // A light, thin stroke that grows with the zoom (none at world zoom); the selected cell's blue
      // outline and the dark "no data" outline stay as they were (T-071).
      getLineColor: (c) =>
        c.cell_id === selectedCellId
          ? [0, 80, 200, 255]
          : needsOutline(c, layer)
            ? [27, 27, 31, 255]
            : [60, 60, 60, CELL_STROKE_ALPHA],
      getLineWidth: (c) => (c.cell_id === selectedCellId ? 3 : needsOutline(c, layer) ? 1.5 : strokeWidth),
      lineWidthUnits: 'pixels',
      updateTriggers: {
        getFillColor: [layer, max],
        getLineColor: [selectedCellId, layer],
        getLineWidth: [selectedCellId, layer, strokeWidth],
      },
      onHover: (info) => {
        const box = wrap.current?.getBoundingClientRect()
        setHover(
          info.object && box
            ? { cell: info.object as MapCell, x: info.x, y: info.y, w: box.width, h: box.height }
            : null,
        )
      },
      onClick: (info) => {
        if (info.object && !clicksIgnored()) {
          const clicked = info.object as MapCell
          pinDispatch({ type: 'click', cellId: clicked.cell_id })
          callbacks.current.onSelectCell(clicked)
        }
      },
    })
    // One icon per cell is a glyph for every one of the 56,238 cells; at world zoom a cell is about 2 px,
    // so the icons would cover the land in black. They appear when a cell can hold one.
    const icons =
      layer === 'verdict' && zoom >= ICON_MIN_ZOOM
        ? [
            new TextLayer<MapCell>({
              id: 'cell-icons',
              data: cells as MapCell[],
              pickable: false,
              getPosition: (c) => [(c.lon_min + c.lon_max) / 2, (c.lat_min + c.lat_max) / 2],
              getText: (c) => VERDICT_PRESENTATION[c.verdict].icon,
              getSize: 13,
              getColor: [20, 20, 20, 255],
              fontFamily: 'system-ui, sans-serif',
              // The icons are not ASCII (▲ ▼ ● ○): without this deck.gl draws only the ASCII ones (the ?).
              characterSet: 'auto',
            }),
          ]
        : []
    overlay.setProps({ layers: [polygons, ...icons, ...outline] })
  }, [cells, layer, selectedCellId, zoom, hoverOutline])

  return (
    <div ref={wrap} className="map-wrap" onMouseLeave={() => setHover(null)}>
      <div
        ref={container}
        className="map"
        role="region"
        aria-label="Global fire activity map"
        aria-busy={loading}
      />
      {loading && <MapLoading />}
      <ScrollHint />
      <MapLegend layer={layer} max={legendMax} cardPinned={pinnedCell !== null} />
      {pinnedCell !== null && <PinnedCellCard cell={pinnedCell} layer={layer} onClose={closePinned} onPointerEnter={() => setHover(null)} />}
      {hover !== null && tooltipCellId(hover.cell.cell_id, pinned, false) !== null && cells !== null && cells.length > 0 && hover.cell.year === cells[0].year && hover.cell.month === cells[0].month && (
        <div
          className="map-tooltip"
          // Flip to the other side of the pointer near the right and bottom edges.
          style={{
            ...(hover.x > hover.w / 2 ? { right: hover.w - hover.x + 12 } : { left: hover.x + 12 }),
            ...(hover.y > hover.h / 2
              ? { bottom: hover.h - hover.y + 12, maxHeight: Math.max(hover.y - 24, 120) }
              : { top: hover.y + 12, maxHeight: Math.max(hover.h - hover.y - 24, 120) }),
          }}
          role="tooltip"
        >
          <CellInfo cell={hover.cell} layer={layer} />
        </div>
      )}
    </div>
  )
}
