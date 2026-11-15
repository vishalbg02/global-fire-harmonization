/** The tabs of the detail card. The selected one is kept in the link as `tab=`. */
export const TAB_IDS = ['calendar', 'satellites', 'evidence', 'anomalies', 'analytics'] as const
export type TabId = (typeof TAB_IDS)[number]

export const TAB_PARAM = 'tab'
export const DEFAULT_TAB: TabId = 'calendar'

/** The tab a link asks for; an invalid or missing value gives the default. */
export function tabFromSearch(search: string): TabId {
  const value = new URLSearchParams(search).get(TAB_PARAM)
  return (TAB_IDS as readonly string[]).includes(value ?? '') ? (value as TabId) : DEFAULT_TAB
}

/** Writes the tab into link parameters; the default tab is left out to keep links short. */
export function setTabParam(params: URLSearchParams, tab: TabId): void {
  if (tab === DEFAULT_TAB) params.delete(TAB_PARAM)
  else params.set(TAB_PARAM, tab)
}

/** The Analytics tab serves countries, continents and the world; a custom area has no stored series for it. */
export const analyticsAvailable = (entityType: string): boolean => entityType !== 'CUSTOM'

/** The tab to show: a link asking for Analytics on a custom area falls back to the default tab. */
export function effectiveTab(tab: TabId, entityType: string): TabId {
  return tab === 'analytics' && !analyticsAvailable(entityType) ? DEFAULT_TAB : tab
}
