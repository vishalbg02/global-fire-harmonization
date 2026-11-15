// Map wiring for the GIBS imagery (T-084): raster sources and layers, the casings that keep outlines
// readable over imagery, and the tile-error counters behind the single failure note.
import type { Map as MapLibreMap, StyleSpecification } from 'maplibre-gl'
import { BASEMAP, TRUE_COLOUR, basemapTileUrl, imageryFailed, trueColourTileUrl } from './gibs.ts'
import type { TileStats } from './gibs.ts'

/** Whether the Flat / Globe switch is offered: only if the cells render correctly on the globe (see the PR). */
export const GLOBE_OFFERED = true

export const BASEMAP_SOURCE = 'gibs-basemap'
export const BASEMAP_LAYER = 'gibs-basemap-layer'
export const TRUE_COLOUR_SOURCE = 'gibs-true-colour'
export const TRUE_COLOUR_LAYER = 'gibs-true-colour-layer'
const PLAIN_BACKGROUND = '#dbe7f1'

/**
 * The map style. The plain background is always there (the fallback); the Blue Marble raster is added
 * unless this is the offline copy, which never asks GIBS.
 */
export function buildStyle(withImagery: boolean): StyleSpecification {
  return {
    version: 8,
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
 * Paint of the country layers for the plain background or over imagery. Over imagery the land fill is
 * invisible (it stays for clicks), and the borders and outlines get a pale casing so they read on dark
 * ocean and on bright cloud alike.
 */
export function paintForImagery(map: MapLibreMap, over: boolean): void {
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
