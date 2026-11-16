import { useCallback, useEffect, useMemo, useReducer, useRef, useState } from 'react'
import * as maplibregl from 'maplibre-gl'
import type { MapGeoJSONFeature, MapMouseEvent } from 'maplibre-gl'
import 'maplibre-gl/dist/maplibre-gl.css'
import maplibreWorkerUrl from 'maplibre-gl/dist/maplibre-gl-worker.mjs?worker&url'
import { MapLibreOverlay } from '@deck.gl/maplibre'
import { GeoJsonLayer, PolygonLayer, TextLayer } from '@deck.gl/layers'
import { TerraDraw, TerraDrawPolygonMode, TerraDrawRectangleMode } from 'terra-draw'
import { TerraDrawMapLibreGLAdapter } from 'terra-draw-maplibre-gl-adapter'
import type { Bbox, MapCell, MapLayer } from '../../api/contract.ts'
import { PAUSE_ROTATION, PAUSE_ROTATION_TITLE, RESUME_ROTATION_TITLE } from '../../content/earth.ts'
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
import { polygonBounds } from './countryBounds.ts'
import { STATIC_ONLY, staticManifest, useStaticManifest } from '../../api/staticData.ts'
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
import { ImageryCredit } from './ImageryControls.tsx'
import type { Dispatch } from 'react'
import type { MapViewAction, MapViewState } from '../../state/mapView.ts'
import { CELL_CASING_IMAGERY, cellOpacity, imageryNote, satDate, todayIso } from './gibs.ts'
import { fadeZoom, quietAlpha, signalFill } from './signal.ts'
import {
  WORLD_CENTER,
  fitPadding,
  flyOptions,
  globeWorldZoom,
  idleLongEnough,
  nextLongitude,
  readRotationPaused,
  rotationAllowed,
  writeRotationPaused,
} from './globeMotion.ts'
import type { Padding } from './globeMotion.ts'
import {
  TileCounter,
  buildStyle,
  hideImagery,
  layerKeyOfSource,
  paintForImagery,
  syncTrueColour,
} from './imagery.ts'

// MapLibre 6 runs in a module worker. Bundlers do not emit it automatically, so register
// it through Vite (works in both the dev server and the production build).
maplibregl.setWorkerUrl(maplibreWorkerUrl)

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
  /** The selected month: Satellite view shows a day of it (T-084). */
  month?: { year: number; month: number } | null
  /** The view choices (shape, Satellite view, day, show all verdicts): owned by the app and kept in the link (T-093). */
  view: MapViewState
  /** Changes a view choice from the map itself (the legend's "Show all verdicts", the fallback to flat when the globe cannot render). */
  onView?: Dispatch<MapViewAction>
  /** Tells the app which imagery could not be loaded, for the note beside the Satellite view control. */
  onImageryStatus?: (status: { basemapFailed: boolean; trueColourFailed: boolean }) => void
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
  return typeof window !== 'undefined' && window.matchMedia(REDUCED_MOTION).matches
}

const REDUCED_MOTION = '(prefers-reduced-motion: reduce)'

/** Whether the user prefers reduced motion, kept up to date when the setting changes. */
function useReducedMotion(): boolean {
  const [reduced, setReduced] = useState(prefersReducedMotion)
  useEffect(() => {
    if (typeof window === 'undefined') return
    const query = window.matchMedia(REDUCED_MOTION)
    const onChange = () => setReduced(query.matches)
    query.addEventListener('change', onChange)
    return () => query.removeEventListener('change', onChange)
  }, [])
  return reduced
}

function localStore(): Storage | null {
  try {
    return typeof window === 'undefined' ? null : window.localStorage
  } catch {
    return null
  }
}

const sameBox = (a: Bbox, b: Bbox) => a.every((v, i) => v === b[i])

/**
 * The space the floating panels take on the map, for fitting an area beside them, not under them: the dock (top left,
 * outside this component, found by its class) and the legend strip (bottom left) on the left, the zoom buttons on the
 * right, the credit line at the bottom. On a phone, where a panel spans most of the width, its height is kept free.
 */
function reservedSpace(container: HTMLElement): Padding {
  const box = container.getBoundingClientRect()
  const reserved: Padding = { top: 0, right: 44, bottom: 24, left: 0 }
  const dock = container.closest('.stage')?.querySelector<HTMLElement>('.dock')?.getBoundingClientRect()
  if (dock !== undefined && dock.width > 0) {
    if (dock.right - box.left > box.width / 2) reserved.top = Math.max(0, dock.bottom - box.top)
    else reserved.left = Math.max(0, dock.right - box.left)
  }
  const legend = container.parentElement?.querySelector<HTMLElement>('.map-legend')?.getBoundingClientRect()
  if (legend !== undefined && legend.width > 0) {
    if (legend.right - box.left > box.width / 2) reserved.bottom = Math.max(reserved.bottom, box.bottom - legend.top)
    else reserved.left = Math.max(reserved.left, legend.right - box.left)
  }
  return reserved
}

/**
 * The world view: on the globe, the Earth centred at `lng` and filling most of the stage; on the flat map, the world box
 * fitted as at the start. Animated like a fly-to unless `instant`.
 */
function showWorld(map: maplibregl.Map, shape: MapViewState['shape'], instant: boolean, lng: number): void {
  const options = flyOptions(instant)
  if (shape === 'globe') {
    const box = map.getContainer()
    map.flyTo({ center: [lng, WORLD_CENTER[1]], zoom: globeWorldZoom(box.clientWidth, box.clientHeight), ...options })
    return
  }
  map.fitBounds(
    [
      [WORLD_BBOX[0], WORLD_BBOX[1]],
      [WORLD_BBOX[2], WORLD_BBOX[3]],
    ],
    { padding: 30, ...options },
  )
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
  month = null,
  view,
  onView,
  onImageryStatus,
}: Props) {
  const container = useRef<HTMLDivElement>(null)
  const mapRef = useRef<maplibregl.Map | null>(null)
  const overlayRef = useRef<MapLibreOverlay | null>(null)
  const loaded = useRef(false)
  const wrap = useRef<HTMLDivElement>(null)
  // Imagery (T-084): Blue Marble under the cells; Satellite view is a day of Aqua true colour.
  const manifest = useStaticManifest()
  const offlineCopy = STATIC_ONLY || manifest !== null
  const offlineAtStart = useRef(STATIC_ONLY || staticManifest() !== null)
  // The shape, Satellite view and its day come from the app (one state, kept in the link).
  const { shape, satOn, satDay } = view
  /** The projection the map has now: a new map starts flat (mercator). */
  const projected = useRef<MapViewState['shape']>('flat')
  /** False until the first projection is applied at load (that one is instant). */
  const projectionApplied = useRef(false)
  const shapeRef = useRef(shape)
  /** True while nothing is selected: a change of shape then shows the whole world in the new one. */
  const atWorld = useRef(true)
  const [overlayGen, setOverlayGen] = useState(0)
  const [basemapFailed, setBasemapFailed] = useState(false)
  const [failedTcDate, setFailedTcDate] = useState<string | null>(null)
  const today = useMemo(() => todayIso(), [])
  const tcDate = !offlineCopy && satOn && month !== null ? satDate(month.year, month.month, satDay, today) : null
  const tcFailed = tcDate !== null && failedTcDate === tcDate
  const tcShown = tcDate !== null && !tcFailed
  const basemapShown = !offlineCopy && !basemapFailed
  const imageryVisible = basemapShown || tcShown
  const tcDateRef = useRef<string | null>(null)
  const imageryRef = useRef<{ visible: boolean; date: string | null }>({ visible: false, date: null })
  const tiles = useRef(new TileCounter())
  // Zoom of the map: the verdict icons are drawn only when a cell is big enough to hold one.
  const [zoom, setZoom] = useState(INITIAL_ZOOM)
  // "Signal, not noise" (signal.ts): the zoom of the fade is followed during a zoom, in small steps, not only at its end.
  const [fade, setFade] = useState(() => fadeZoom(INITIAL_ZOOM))
  const quiet = quietAlpha(fade, view.showAll)
  const reducedMotion = useReducedMotion()
  // Idle rotation of the globe (globeMotion.ts): the user's pause is remembered; any interaction stops it for 8 s.
  const [rotationPaused, setRotationPaused] = useState(() => readRotationPaused(localStore()))
  const lastInteraction = useRef(Date.now())
  const stopRotation = useRef<() => void>(() => {})
  const clearCountryHover = useRef<() => void>(() => {})
  // The cell under the pointer, outlined on the map (T-093); changes only when the pointer enters another cell.
  const [hoverCell, setHoverCell] = useState<MapCell | null>(null)
  const motion = useRef({ shape, paused: rotationPaused, drawing: false, pinned: false, reducedMotion })
  // The outline of the country under the pointer, drawn above the cells (T-070).
  const [hoverOutline, setHoverOutline] = useState<unknown>(null)
  const countryShapes = useRef<Map<string, unknown> | null>(null)
  // True once the country shapes are read: the selected country's outline and fit use them.
  const [shapesReady, setShapesReady] = useState(false)
  const [hover, setHover] = useState<{ cell: MapCell; x: number; y: number; w: number; h: number } | null>(null)
  const callbacks = useRef({ onSelectCell, onSelectCountry, onDrawn, onDrawnPolygon, onHoverCountry, onView })
  // The cell whose card is pinned on the map: until closed, Esc, or another cell is clicked (T-071).
  const [pinned, pinDispatch] = useReducer(pinnedReducer, null)
  useEffect(() => pinDispatch({ type: 'selection', selectedCellId }), [selectedCellId])
  const closePinned = useCallback(() => {
    // The card is removed, so focus that was inside it goes back to the map instead of being lost (T-074).
    const active = document.activeElement
    const hadFocus = active instanceof HTMLElement && active.closest('.map-pinned') !== null
    pinDispatch({ type: 'dismiss' })
    if (hadFocus) mapRef.current?.getCanvas().focus()
  }, [])
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
    callbacks.current = { onSelectCell, onSelectCountry, onDrawn, onDrawnPolygon, onHoverCountry, onView }
    drawingRef.current = drawing || polygonDrawing
    shapeRef.current = shape
    motion.current = { shape, paused: rotationPaused, drawing: drawing || polygonDrawing, pinned: pinned !== null, reducedMotion }
    atWorld.current =
      (fit === null || sameBox(fit.bbox, WORLD_BBOX)) && selectedCountryIso3 === null && customBbox === null && customRing === null
  })
  useEffect(() => {
    tcDateRef.current = tcDate
    imageryRef.current = { visible: imageryVisible, date: tcShown ? tcDate : null }
  })
  const clicksIgnored = () => drawingRef.current || Date.now() < ignoreClicksUntil.current

  useEffect(() => {
    if (container.current === null) return
    const map = new maplibregl.Map({
      container: container.current,
      style: buildStyle(!offlineAtStart.current),
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
    // The cells canvas of the overlay is only a picture: the map canvas above is the one keyboard stop.
    // (deck.gl makes its canvas focusable and puts the tabindex back, which gave a second, unnamed Tab stop;
    // `inert` removes it from focus and from the accessibility tree, and the canvas takes no pointer events.)
    const hideOverlayCanvas = () =>
      map
        .getContainer()
        .querySelectorAll<HTMLCanvasElement>('canvas:not(.maplibregl-canvas)')
        .forEach((c) => {
          c.inert = true
        })
    hideOverlayCanvas()
    map.on('load', hideOverlayCanvas)
    mapRef.current = map
    overlayRef.current = overlay
    projected.current = 'flat'
    projectionApplied.current = false
    setZoom(map.getZoom())
    setFade(fadeZoom(map.getZoom()))
    map.on('zoomend', () => {
      setZoom(map.getZoom())
      setFade(fadeZoom(map.getZoom()))
    })
    // The globe needs more of the graphics card than the flat map: if the context is lost, fall back to flat silently.
    map.on('webglcontextlost', () => {
      if (projected.current === 'globe') callbacks.current.onView?.({ type: 'set-shape', shape: 'flat' })
    })
    // During a zoom (a wheel, a pinch, a fly-to), once per frame at most; React re-renders only when a step is crossed.
    let zoomFrame = 0
    map.on('zoom', () => {
      if (zoomFrame !== 0) return
      zoomFrame = requestAnimationFrame(() => {
        zoomFrame = 0
        setFade(fadeZoom(map.getZoom()))
      })
    })
    // Imagery tiles: count loaded and failed ones; a failed layer is hidden and the plain background shows.
    map.on('data', (e) => {
      if (e.dataType !== 'source' || !('tile' in e) || e.tile === undefined) return
      const key = layerKeyOfSource((e as { sourceId?: string }).sourceId)
      if (key !== null) tiles.current.ok(key)
    })
    map.on('error', (e) => {
      const key = layerKeyOfSource((e as { sourceId?: string }).sourceId)
      if (key === null || !tiles.current.fail(key)) return
      hideImagery(map, key)
      if (key === 'basemap') setBasemapFailed(true)
      else setFailedTcDate(tcDateRef.current)
    })

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
        setShapesReady(true)
      })
      .catch(() => {
        countryShapes.current = null
      })

    map.on('load', () => {
      map.addSource('countries', { type: 'geojson', data: COUNTRIES_URL })
      map.addLayer({ id: 'countries-fill', type: 'fill', source: 'countries', paint: { 'fill-color': '#f7f7f2', 'fill-opacity': 1 } })
      // Over imagery a dark casing under the white border keeps it readable on cloud (T-084).
      map.addLayer({
        id: 'countries-line-casing',
        type: 'line',
        source: 'countries',
        layout: { visibility: 'none' },
        paint: { 'line-color': '#14181f', 'line-opacity': 0.2, 'line-width': 1.5 },
      })
      map.addLayer({ id: 'countries-line', type: 'line', source: 'countries', paint: { 'line-color': '#8a8f98', 'line-width': 0.6 } })
      map.addLayer({
        id: 'anomalies-casing',
        type: 'line',
        source: 'countries',
        layout: { visibility: 'none' },
        paint: { 'line-color': '#ffffff', 'line-opacity': 0.6, 'line-width': 3.5 },
        filter: ['in', ['get', 'ISO_A3_EH'], ['literal', []]],
      })
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
        id: 'countries-selected-casing',
        type: 'line',
        source: 'countries',
        layout: { visibility: 'none' },
        paint: { 'line-color': '#ffffff', 'line-opacity': 0.7, 'line-width': 4 },
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
      // Imagery state at load: Satellite view may already be on (month known) and the casings are set.
      paintForImagery(map, imageryRef.current.visible)
      syncTrueColour(map, imageryRef.current.date)
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
    clearCountryHover.current = () => setHover(null)
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
      if (zoomFrame !== 0) cancelAnimationFrame(zoomFrame)
      clearCountryHover.current = () => {}
      map.remove()
      mapRef.current = null
      overlayRef.current = null
    }
  }, [])

  // Idle rotation (globeMotion.ts): on the globe at the world view, after 8 s without interaction, the Earth turns slowly
  // eastward. Any pointer, wheel, touch or key on the map, a selection or a fit stops it at once; it never runs while
  // drawing, with a pinned card, in a hidden tab, under reduced motion or when paused with the map's button.
  useEffect(() => {
    const map = mapRef.current
    if (map === null) return
    let frame = 0
    let last = 0
    const conditions = () => {
      const box = map.getContainer()
      return {
        ...motion.current,
        zoom: map.getZoom(),
        worldZoom: globeWorldZoom(box.clientWidth, box.clientHeight),
        hidden: document.hidden,
      }
    }
    const stop = () => {
      if (frame !== 0) cancelAnimationFrame(frame)
      frame = 0
    }
    const step = (t: number) => {
      if (!rotationAllowed(conditions()) || map.isMoving()) {
        frame = 0
        return
      }
      const dt = last === 0 ? 0 : t - last
      last = t
      const center = map.getCenter()
      map.jumpTo({ center: [nextLongitude(center.lng, dt), center.lat] })
      frame = requestAnimationFrame(step)
    }
    const check = () => {
      if (frame !== 0 || !loaded.current || map.isMoving()) return
      if (!rotationAllowed(conditions()) || !idleLongEnough(Date.now(), lastInteraction.current)) return
      // The pointer may rest on the map: its tooltip and outlines would no longer match what is under it.
      setHover(null)
      setHoverCell(null)
      clearCountryHover.current()
      last = 0
      frame = requestAnimationFrame(step)
    }
    const interact = () => {
      lastInteraction.current = Date.now()
      stop()
    }
    stopRotation.current = interact
    const timer = window.setInterval(check, 500)
    const el = map.getContainer()
    const events = ['pointerdown', 'pointermove', 'wheel', 'touchstart', 'keydown'] as const
    for (const type of events) el.addEventListener(type, interact, { passive: true })
    const onVisibility = () => {
      if (document.hidden) stop()
    }
    document.addEventListener('visibilitychange', onVisibility)
    return () => {
      window.clearInterval(timer)
      stop()
      for (const type of events) el.removeEventListener(type, interact)
      document.removeEventListener('visibilitychange', onVisibility)
      stopRotation.current = () => {}
    }
  }, [])

  // A new selection or a drawing mode is an interaction: the rotation waits another 8 s.
  useEffect(() => stopRotation.current(), [selectedCellId, selectedCountryIso3, drawing, polygonDrawing])

  const toggleRotation = () => {
    const next = !rotationPaused
    stopRotation.current()
    setRotationPaused(next)
    writeRotationPaused(localStore(), next)
  }

  // Satellite view: add, change or remove the day's true-colour layer.
  useEffect(() => {
    const map = mapRef.current
    if (map === null) return
    const apply = () => {
      tiles.current.reset('true-colour')
      syncTrueColour(map, tcDate)
    }
    if (loaded.current) apply()
    else map.once('load', apply)
  }, [tcDate])

  // Country layers: plain land fill on the plain background, invisible fill and casings over imagery.
  useEffect(() => {
    const map = mapRef.current
    if (map === null) return
    const apply = () => paintForImagery(map, imageryVisible)
    if (loaded.current) apply()
    else map.once('load', apply)
  }, [imageryVisible])

  // The offline copy (manifest found after the map was made): hide any imagery that was requested.
  useEffect(() => {
    const map = mapRef.current
    if (map === null || !offlineCopy) return
    const apply = () => hideImagery(map, 'both')
    if (loaded.current) apply()
    else map.once('load', apply)
  }, [offlineCopy])

  // The projection follows the shape of the app's state, at load and at every change: the control, the map and the link
  // read the same value (T-093). The cells overlay picks its view (flat or globe) when it is made, so a new one is made.
  // If the globe cannot be drawn here, the app's state goes back to flat, so the control and the link follow.
  useEffect(() => {
    const map = mapRef.current
    if (map === null) return
    const apply = () => {
      if (projected.current === shape) return
      const first = !projectionApplied.current
      projectionApplied.current = true
      try {
        map.setProjection({ type: shape === 'globe' ? 'globe' : 'mercator' })
      } catch {
        if (shape === 'globe') callbacks.current.onView?.({ type: 'set-shape', shape: 'flat' })
        return
      }
      projected.current = shape
      if (overlayRef.current !== null) map.removeControl(overlayRef.current)
      const overlay = new MapLibreOverlay({ interleaved: false, layers: [] })
      map.addControl(overlay)
      overlayRef.current = overlay
      setOverlayGen((g) => g + 1)
      // At the world view the whole world is shown in the new shape: the globe at its size, the flat map fitted.
      if (atWorld.current && map.getZoom() < 3) {
        showWorld(map, shape, first || prefersReducedMotion(), first ? WORLD_CENTER[0] : map.getCenter().lng)
      }
    }
    if (loaded.current) apply()
    else map.once('load', apply)
    return () => {
      map.off('load', apply)
    }
  }, [shape])

  useEffect(() => {
    onImageryStatus?.({ basemapFailed, trueColourFailed: tcFailed })
    // eslint-disable-next-line react-hooks/exhaustive-deps -- the callback is read at that moment
  }, [basemapFailed, tcFailed])

  // A new Satellite day or month is tried afresh.
  useEffect(() => setFailedTcDate(null), [satOn])

  useEffect(() => {
    const map = mapRef.current
    if (map === null) return
    const apply = () => {
      map.setFilter('countries-selected', ['==', ['get', 'ISO_A3_EH'], selectedCountryIso3 ?? ''])
      map.setFilter('countries-selected-casing', ['==', ['get', 'ISO_A3_EH'], selectedCountryIso3 ?? ''])
    }
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
      map.setFilter('anomalies-casing', ['in', ['get', 'ISO_A3_EH'], ['literal', [...anomalyOutlines.above, ...anomalyOutlines.below]]])
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

  // Fly to an area chosen in the picker, a story or an anomaly (about 1.2 s, ease-out; instant under reduced motion),
  // fitted beside the floating panels, not under them. Choosing the world flies back to the world view.
  useEffect(() => {
    const map = mapRef.current
    if (map === null || fit === null) return
    stopRotation.current()
    const reduced = prefersReducedMotion()
    if (selectedCountryIso3 === null && sameBox(fit.bbox, WORLD_BBOX)) {
      showWorld(map, shapeRef.current, reduced, map.getCenter().lng)
      return
    }
    // A selected country: its boundary's box (the cells stop short of the far north); else the box asked for.
    const shape = selectedCountryIso3 === null ? null : countryShapes.current?.get(selectedCountryIso3)
    const [w, s, e, n] = (shape === undefined || shape === null ? null : polygonBounds(shape)) ?? fit.bbox
    const box = map.getContainer()
    map.fitBounds(
      [
        [w, s],
        [e, n],
      ],
      { padding: fitPadding(box.clientWidth, box.clientHeight, reservedSpace(box)), maxZoom: 6, ...flyOptions(reduced) },
    )
    // eslint-disable-next-line react-hooks/exhaustive-deps -- a new fit, or the shapes arriving, refits; the country is read at that moment
  }, [fit, shapesReady])

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
    const opacity = cellOpacity(imageryVisible)
    const outline: GeoJsonLayer[] =
      hoverOutline === null
        ? []
        : [
            // Over imagery the dark hover outline gets a pale casing underneath (T-084).
            ...(imageryVisible
              ? [
                  new GeoJsonLayer({
                    id: 'hover-outline-casing',
                    // eslint-disable-next-line @typescript-eslint/no-explicit-any -- one Natural Earth feature, read from the countries file
                    data: hoverOutline as any,
                    pickable: false,
                    stroked: true,
                    filled: false,
                    getLineColor: [255, 255, 255, 170],
                    getLineWidth: 5,
                    lineWidthUnits: 'pixels',
                  }),
                ]
              : []),
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
    // The selected country's outline, above the cells like the hover outline (T-070 follow-up).
    const selectedShape = selectedCountryIso3 === null ? null : (countryShapes.current?.get(selectedCountryIso3) ?? null)
    if (selectedShape !== null) {
      outline.push(
        new GeoJsonLayer({
          id: 'selected-country-outline',
          // eslint-disable-next-line @typescript-eslint/no-explicit-any -- one Natural Earth feature, read from the countries file
          data: selectedShape as any,
          pickable: false,
          stroked: true,
          filled: false,
          getLineColor: [0, 80, 200, 255],
          getLineWidth: 3,
          lineWidthUnits: 'pixels',
        }),
      )
    }
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
      // At world zoom the quiet verdicts are drawn faintly (signal.ts); they stay pickable for the tooltip and the card.
      getFillColor: (c) => [...signalFill(cellFillColor(c, layer, max, opacity), c.verdict, layer, quiet)],
      // A light, thin stroke that grows with the zoom (none at world zoom); the selected cell's blue
      // outline and the dark "no data" outline stay as they were (T-071).
      // A quiet cell's thin stroke fades with its fill, so the grid does not come back as noise.
      getLineColor: (c) =>
        c.cell_id === selectedCellId
          ? [0, 80, 200, 255]
          : needsOutline(c, layer)
            ? [27, 27, 31, 255]
            : [...signalFill(imageryVisible ? CELL_CASING_IMAGERY : [60, 60, 60, CELL_STROKE_ALPHA], c.verdict, layer, quiet)],
      getLineWidth: (c) => (c.cell_id === selectedCellId ? 3 : needsOutline(c, layer) ? 1.5 : strokeWidth),
      lineWidthUnits: 'pixels',
      updateTriggers: {
        getFillColor: [layer, max, opacity, quiet],
        getLineColor: [selectedCellId, layer, imageryVisible, quiet],
        getLineWidth: [selectedCellId, layer, strokeWidth],
      },
      onHover: (info) => {
        const box = wrap.current?.getBoundingClientRect()
        const object = (info.object as MapCell | undefined) ?? null
        setHover(object !== null && box ? { cell: object, x: info.x, y: info.y, w: box.width, h: box.height } : null)
        setHoverCell((prev) => (prev?.cell_id === object?.cell_id ? prev : object))
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
    // The selected cell: a pale casing under its blue outline, so it reads on dark and on bright imagery.
    const selected = selectedCellId === null ? undefined : cells.find((c) => c.cell_id === selectedCellId)
    const selectedOutline =
      selected === undefined || !imageryVisible
        ? []
        : [
            new PolygonLayer<MapCell>({
              id: 'selected-casing',
              data: [selected],
              pickable: false,
              stroked: true,
              filled: false,
              getPolygon: (c) => [[c.lon_min, c.lat_min], [c.lon_max, c.lat_min], [c.lon_max, c.lat_max], [c.lon_min, c.lat_max]],
              getLineColor: [255, 255, 255, 240],
              getLineWidth: 6,
              lineWidthUnits: 'pixels',
            }),
            new PolygonLayer<MapCell>({
              id: 'selected-outline',
              data: [selected],
              pickable: false,
              stroked: true,
              filled: false,
              getPolygon: (c) => [[c.lon_min, c.lat_min], [c.lon_max, c.lat_min], [c.lon_max, c.lat_max], [c.lon_min, c.lat_max]],
              getLineColor: [0, 80, 200, 255],
              getLineWidth: 3,
              lineWidthUnits: 'pixels',
            }),
          ]
    // The cell under the pointer (T-093): a thin dark outline, with a pale casing over imagery. Not while drawing.
    const cellRing = (c: MapCell) => [[c.lon_min, c.lat_min], [c.lon_max, c.lat_min], [c.lon_max, c.lat_max], [c.lon_min, c.lat_max]]
    const hovered = hoverCell === null || drawing || polygonDrawing ? [] : [hoverCell]
    const hoverLayers =
      hovered.length === 0
        ? []
        : [
            ...(imageryVisible
              ? [
                  new PolygonLayer<MapCell>({
                    id: 'hover-cell-casing',
                    data: hovered,
                    pickable: false,
                    stroked: true,
                    filled: false,
                    getPolygon: cellRing,
                    getLineColor: [255, 255, 255, 190],
                    getLineWidth: 3.5,
                    lineWidthUnits: 'pixels',
                  }),
                ]
              : []),
            new PolygonLayer<MapCell>({
              id: 'hover-cell',
              data: hovered,
              pickable: false,
              stroked: true,
              filled: false,
              getPolygon: cellRing,
              getLineColor: [20, 24, 31, 235],
              getLineWidth: 1.5,
              lineWidthUnits: 'pixels',
            }),
          ]
    overlay.setProps({ layers: [polygons, ...selectedOutline, ...hoverLayers, ...icons, ...outline] })
  }, [cells, layer, selectedCellId, zoom, hoverOutline, selectedCountryIso3, shapesReady, imageryVisible, overlayGen, quiet, hoverCell, drawing, polygonDrawing])

  return (
    <div
      ref={wrap}
      className="map-wrap"
      data-shape={shape}
      onMouseLeave={() => {
        setHover(null)
        setHoverCell(null)
      }}
    >
      <div
        ref={container}
        className="map"
        role="region"
        aria-label="Global fire activity map"
        aria-busy={loading}
      />
      {loading && <MapLoading />}
      <ImageryCredit
        offlineCopy={offlineCopy}
        satDateShown={tcShown ? tcDate : null}
        note={imageryNote(offlineCopy, basemapFailed, tcFailed)}
        basemapShown={basemapShown}
      />
      <ScrollHint />
      {shape === 'globe' && !reducedMotion && (
        <button
          type="button"
          className="bare map-rotate"
          aria-pressed={rotationPaused}
          aria-label={PAUSE_ROTATION}
          title={rotationPaused ? RESUME_ROTATION_TITLE : PAUSE_ROTATION_TITLE}
          onClick={toggleRotation}
        >
          {rotationPaused ? (
            <svg width="12" height="12" viewBox="0 0 12 12" aria-hidden="true">
              <path d="M3 1.5v9l7.5-4.5z" fill="currentColor" />
            </svg>
          ) : (
            <svg width="12" height="12" viewBox="0 0 12 12" aria-hidden="true">
              <path d="M2.5 1.5h2.5v9H2.5zM7 1.5h2.5v9H7z" fill="currentColor" />
            </svg>
          )}
        </button>
      )}
      <MapLegend
        layer={layer}
        max={legendMax}
        cardPinned={pinnedCell !== null}
        showAll={view.showAll}
        onShowAll={onView === undefined ? undefined : (on) => onView({ type: 'set-show-all', on })}
        ruleActive={quietAlpha(fade, false) < 1}
      />
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
