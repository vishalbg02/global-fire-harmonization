import type { Bbox } from '../../api/contract.ts'

/**
 * West, south, east, north of a GeoJSON Polygon or MultiPolygon feature (the country boundary), or null when the
 * shape is missing or has no usable coordinate. A plain minimum and maximum, as the cell bounds are: a country that
 * Natural Earth splits at 180 degrees (Russia, Fiji) spans -180 to 180, the same box as before (no antimeridian
 * wrapping is attempted).
 */
export function polygonBounds(feature: unknown): Bbox | null {
  const geometry = (feature as { geometry?: { type?: unknown; coordinates?: unknown } } | null | undefined)?.geometry
  if (geometry === null || geometry === undefined) return null
  let west = Infinity
  let south = Infinity
  let east = -Infinity
  let north = -Infinity
  const visit = (node: unknown): void => {
    if (!Array.isArray(node)) return
    if (node.length >= 2 && typeof node[0] === 'number' && typeof node[1] === 'number') {
      const [x, y] = node as number[]
      if (!Number.isFinite(x) || !Number.isFinite(y)) return
      west = Math.min(west, x)
      east = Math.max(east, x)
      south = Math.min(south, y)
      north = Math.max(north, y)
      return
    }
    for (const child of node) visit(child)
  }
  if (geometry.type === 'Polygon' || geometry.type === 'MultiPolygon') visit(geometry.coordinates)
  return Number.isFinite(west) && east > west && north > south ? [west, south, east, north] : null
}
