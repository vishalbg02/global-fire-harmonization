/** The query-string key that shows the methods and validation page. */
export const PAGE_PARAM = 'page'
export const METHODS_PAGE = 'methods'

/** Whether a link's query string asks for the methods page. */
export function pageFromSearch(search: string): 'methods' | 'map' {
  return new URLSearchParams(search).get(PAGE_PARAM) === METHODS_PAGE ? 'methods' : 'map'
}

/**
 * A link to the methods page (optionally to one anchor), keeping the current selection in the
 * address so that "Back to the map" returns to the same view. An ordinary link: it works
 * without scripts and can be shared.
 */
export function methodsHref(anchor?: string, location?: { pathname: string; search: string }): string {
  const loc = location ?? (typeof window === 'undefined' ? { pathname: '/', search: '' } : window.location)
  const params = new URLSearchParams(loc.search)
  params.set(PAGE_PARAM, METHODS_PAGE)
  return `${loc.pathname}?${params.toString()}${anchor === undefined ? '' : `#${anchor}`}`
}

/** The anchor of a reason code on the methods page: the evidence panel links here. */
export const reasonAnchor = (code: string) => `reason-${code}`
