import { FIRMS_URL } from '../export/exportHelpers.ts'
import { methodsHref } from '../../content/methodsLink.ts'
import * as UI from '../../content/ui.ts'
import { useFirmsProducts } from './mapSource.ts'
import type { FirmsProducts } from './mapSource.ts'

/**
 * The source line under the map: the FIRMS products (standard and near-real-time), the grid and
 * the method version from /api/meta, with links. Product names come from the methods page's
 * dataset list; the version is read from the metadata, never written here.
 */
export function MapSourceLine({ methodVersion, products }: { methodVersion: string | null; products?: FirmsProducts | null }) {
  const loaded = useFirmsProducts()
  const list = products === undefined ? loaded : products
  return (
    <p className="source-line map-source">
      <strong>{UI.MAP_SOURCE_LABEL}: </strong>
      <a href={FIRMS_URL} target="_blank" rel="noreferrer">
        NASA FIRMS
      </a>
      {` active-fire products${
        list === null
          ? ''
          : `, ${UI.MAP_SOURCE_STANDARD} ${list.standard.join(', ')} and ${UI.MAP_SOURCE_NRT} ${list.nearRealTime.join(', ')}`
      }; ${UI.MAP_SOURCE_GRID}; ${methodVersion === null ? UI.MAP_SOURCE_METHOD_UNKNOWN : UI.MAP_SOURCE_METHOD(methodVersion)}. `}
      <a href={methodsHref('sources')}>{UI.NAV_METHODS}</a>
    </p>
  )
}
