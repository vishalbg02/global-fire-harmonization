// Map wiring for the GIBS imagery (T-084): raster sources and layers, the casings that keep outlines
// readable over imagery, and the tile-error counters behind the single failure note.
import type { Map as MapLibreMap, SkySpecification, StyleSpecification } from 'maplibre-gl'
import { BASEMAP, TRUE_COLOUR, basemapTileUrl, imageryFailed, trueColourTileUrl } from './gibs.ts'
import type { TileStats } from './gibs.ts'

export const BASEMAP_SOURCE = 'gibs-basemap'
export const BASEMAP_LAYER = 'gibs-basemap-layer'
export const TRUE_COLOUR_SOURCE = 'gibs-true-colour'
export const TRUE_COLOUR_LAYER = 'gibs-true-colour-layer'
export const PLAIN_BACKGROUND = '#dbe7f1'
/**
 * Under imagery the background is a dark ocean blue close to Blue Marble's deep ocean: on the globe, MapLibre leaves a
 * thin band at the limb without raster tiles, and the pale plain background showed there as a bright ring (T-093).
 */
export const IMAGERY_BACKGROUND = '#0e2340'
/** The dark of space behind the globe: the same colour as the stage (--stage in tokens.css). */
export const SPACE_COLOR = '#070b14'

/**
 * Space and atmosphere (T-093). On the globe MapLibre draws a thin atmosphere at the Earth's limb; it is kept subtle
 * and fades out as the user zooms in, where it would only veil the map. The sky colours are the stage's dark, so a
 * tilted view shows space, not a blue sky. The flat map draws no atmosphere, so it looks as before.
 */
export const SPACE_SKY: SkySpecification = {
  'sky-color': SPACE_COLOR,
  'horizon-color': SPACE_COLOR,
  'fog-color': SPACE_COLOR,
  'sky-horizon-blend': 0,
  'horizon-fog-blend': 0,
  'fog-ground-blend': 1,
  'atmosphere-blend': ['interpolate', ['linear'], ['zoom'], 0, 0.6, 2.5, 0.5, 3.5, 0.15, 4.5, 0],
}

/**
 * The map style. The plain background is always there (the fallback); the Blue Marble raster is added
 * unless this is the offline copy, which never asks GIBS.
 */
export function buildStyle(withImagery: boolean): StyleSpecification {
  return {
    version: 8,
    sky: SPACE_SKY,
    sources: withImagery
      ? {
          [BASEMAP_SOURCE]: {
            type: 'raster',
            tiles: [basemapTileUrl()],
            tileSize: 256,
            maxzoom: BASEMAP.maxzoom,
          },
        }
      : {},
    layers: [
      { id: 'background', type: 'background', paint: { 'background-color': PLAIN_BACKGROUND } },
      ...(withImagery ? [{ id: BASEMAP_LAYER, type: 'raster' as const, source: BASEMAP_SOURCE }] : []),
    ],
  }
}

/** Show the true-colour layer for `date` (YYYY-MM-DD), or remove it when `date` is null. */
export function syncTrueColour(map: MapLibreMap, date: string | null): void {
  if (map.getLayer(TRUE_COLOUR_LAYER) !== undefined) map.removeLayer(TRUE_COLOUR_LAYER)
  if (map.getSource(TRUE_COLOUR_SOURCE) !== undefined) map.removeSource(TRUE_COLOUR_SOURCE)
  if (date === null) return
  map.addSource(TRUE_COLOUR_SOURCE, {
    type: 'raster',
    tiles: [trueColourTileUrl(date)],
    tileSize: 256,
    maxzoom: TRUE_COLOUR.maxzoom,
  })
  // Above the Blue Marble, below the country layers.
  map.addLayer({ id: TRUE_COLOUR_LAYER, type: 'raster', source: TRUE_COLOUR_SOURCE }, map.getLayer('countries-fill') ? 'countries-fill' : undefined)
}

/** Hide the imagery layers (after a failure): the plain background shows. */
export function hideImagery(map: MapLibreMap, which: 'basemap' | 'true-colour' | 'both'): void {
  if (which !== 'true-colour' && map.getLayer(BASEMAP_LAYER) !== undefined) map.setLayoutProperty(BASEMAP_LAYER, 'visibility', 'none')
  if (which !== 'basemap' && map.getLayer(TRUE_COLOUR_LAYER) !== undefined) map.setLayoutProperty(TRUE_COLOUR_LAYER, 'visibility', 'none')
}

/**
 * Paint of the background and the country layers for the plain background or over imagery. Over imagery the
 * land fill is invisible (it stays for clicks), the background is the dark ocean, and the borders and outlines
 * get a pale casing so they read on dark ocean and on bright cloud alike.
 */
export function paintForImagery(map: MapLibreMap, over: boolean): void {
  if (map.getLayer('background') !== undefined) map.setPaintProperty('background', 'background-color', over ? IMAGERY_BACKGROUND : PLAIN_BACKGROUND)
  if (map.getLayer('countries-fill') === undefined) return
  map.setPaintProperty('countries-fill', 'fill-opacity', over ? 0 : 1)
  map.setPaintProperty('countries-line', 'line-color', over ? '#f4f4ee' : '#8a8f98')
  map.setPaintProperty('countries-line', 'line-width', over ? 0.6 : 0.6)
  for (const id of ['countries-line-casing', 'anomalies-casing', 'countries-selected-casing']) {
    if (map.getLayer(id) !== undefined) map.setLayoutProperty(id, 'visibility', over ? 'visible' : 'none')
  }
}

export type ImageryLayerKey = 'basemap' | 'true-colour'

/** Counts of loaded and failed tiles per imagery layer, fed from the map's 'data' and 'error' events. */
export class TileCounter {
  private stats: Record<ImageryLayerKey, TileStats> = { basemap: { ok: 0, failed: 0 }, 'true-colour': { ok: 0, failed: 0 } }
  reset(key: ImageryLayerKey): void {
    this.stats[key] = { ok: 0, failed: 0 }
  }
  ok(key: ImageryLayerKey): void {
    this.stats[key].ok++
  }
  fail(key: ImageryLayerKey): boolean {
    this.stats[key].failed++
    return imageryFailed(this.stats[key])
  }
}

export function layerKeyOfSource(sourceId: string | undefined): ImageryLayerKey | null {
  if (sourceId === BASEMAP_SOURCE) return 'basemap'
  if (sourceId === TRUE_COLOUR_SOURCE) return 'true-colour'
  return null
}
