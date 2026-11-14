import { useEffect, useRef, useState } from 'react'
import * as maplibregl from 'maplibre-gl'
import type { MapGeoJSONFeature, MapMouseEvent, StyleSpecification } from 'maplibre-gl'
import 'maplibre-gl/dist/maplibre-gl.css'
import maplibreWorkerUrl from 'maplibre-gl/dist/maplibre-gl-worker.mjs?worker&url'
import { MapLibreOverlay } from '@deck.gl/maplibre'
import { PolygonLayer, TextLayer } from '@deck.gl/layers'
import { TerraDraw, TerraDrawRectangleMode } from 'terra-draw'
import { TerraDrawMapLibreGLAdapter } from 'terra-draw-maplibre-gl-adapter'
import type { Bbox, MapCell, MapLayer } from '../../api/contract.ts'
import { bboxFromRing } from '../../state/bbox.ts'
import type { FitRequest } from '../../state/selection.ts'
import { VERDICT_PRESENTATION } from '../../content/verdicts.ts'
import { CellInfo } from './CellInfo.tsx'
import { countryIso3, countryName } from './countries.ts'
import { cellFillColor, sharedMax } from './scale.ts'

// MapLibre 6 runs in a module worker. Bundlers do not emit it automatically, so register
// it through Vite (works in both the dev server and the production build).
maplibregl.setWorkerUrl(maplibreWorkerUrl)

// A plain background: no external tiles, so no key and it works offline.
const STYLE: StyleSpecification = {
  version: 8,
  sources: {},
  layers: [{ id: 'background', type: 'background', paint: { 'background-color': '#dbe7f1' } }],
}

const COUNTRIES_URL = `${import.meta.env.BASE_URL}geo/ne_110m_admin_0_countries.geojson`

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
  /** While true, the user draws a rectangle with two clicks. */
  drawing: boolean
  onDrawn: (bbox: Bbox) => void
  /** ISO3 codes of the countries listed in the anomaly rankings, to outline (T-040). */
  anomalyOutlines: { above: readonly string[]; below: readonly string[] }
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
  drawing,
  onDrawn,
  anomalyOutlines,
}: Props) {
  const container = useRef<HTMLDivElement>(null)
  const mapRef = useRef<maplibregl.Map | null>(null)
  const overlayRef = useRef<MapLibreOverlay | null>(null)
  const loaded = useRef(false)
  const wrap = useRef<HTMLDivElement>(null)
  const [hover, setHover] = useState<{ cell: MapCell; x: number; y: number; w: number; h: number } | null>(null)
  const callbacks = useRef({ onSelectCell, onSelectCountry, onDrawn })
  // Clicks are ignored while drawing, and for a moment after a rectangle is finished, so that
  // the click that ends the drawing does not also select a country or a cell.
  const ignoreClicksUntil = useRef(0)
  const drawingRef = useRef(drawing)
  useEffect(() => {
    callbacks.current = { onSelectCell, onSelectCountry, onDrawn }
    drawingRef.current = drawing
  })
  const clicksIgnored = () => drawingRef.current || Date.now() < ignoreClicksUntil.current

  useEffect(() => {
    if (container.current === null) return
    const map = new maplibregl.Map({
      container: container.current,
      style: STYLE,
      center: [10, 20],
      zoom: 1.2,
      renderWorldCopies: false,
      attributionControl: false,
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
    map.on('mouseenter', 'countries-fill', () => (map.getCanvas().style.cursor = 'pointer'))
    map.on('mouseleave', 'countries-fill', () => (map.getCanvas().style.cursor = ''))

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
      source?.setData({ type: 'FeatureCollection', features: customBbox === null ? [] : [boxFeature(customBbox)] })
    }
    if (loaded.current) apply()
    else map.once('load', apply)
  }, [customBbox])

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

  useEffect(() => {
    const overlay = overlayRef.current
    if (overlay === null) return
    if (cells === null || cells.length === 0) {
      overlay.setProps({ layers: [] })
      return
    }
    const max = sharedMax(cells)
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
      getLineColor: (c) => (c.cell_id === selectedCellId ? [0, 80, 200, 255] : [60, 60, 60, 90]),
      getLineWidth: (c) => (c.cell_id === selectedCellId ? 3 : 1),
      lineWidthUnits: 'pixels',
      updateTriggers: { getFillColor: [layer, max], getLineColor: [selectedCellId], getLineWidth: [selectedCellId] },
      onHover: (info) => {
        const box = wrap.current?.getBoundingClientRect()
        setHover(
          info.object && box
            ? { cell: info.object as MapCell, x: info.x, y: info.y, w: box.width, h: box.height }
            : null,
        )
      },
      onClick: (info) => {
        if (info.object && !clicksIgnored()) callbacks.current.onSelectCell(info.object as MapCell)
      },
    })
    const icons =
      layer === 'verdict'
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
            }),
          ]
        : []
    overlay.setProps({ layers: [polygons, ...icons] })
  }, [cells, layer, selectedCellId])

  return (
    <div ref={wrap} className="map-wrap" onMouseLeave={() => setHover(null)}>
      <div ref={container} className="map" role="region" aria-label="Global fire activity map" />
      {hover !== null && cells !== null && cells.length > 0 && hover.cell.year === cells[0].year && hover.cell.month === cells[0].month && (
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
