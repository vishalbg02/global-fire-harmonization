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

/** The last Details tab the user opened, remembered in this browser only (nothing is sent anywhere). */
export const TAB_STORAGE_KEY = 'gfh.details.tab'

type TabStore = Pick<Storage, 'getItem' | 'setItem'>

function localStore(): TabStore | null {
  try {
    return typeof window === 'undefined' ? null : window.localStorage
  } catch {
    return null
  }
}

const isTab = (value: string | null): value is TabId => (TAB_IDS as readonly string[]).includes(value ?? '')

/**
 * The tab to open with: a valid `tab=` in the link always wins; without one, the tab the user last opened; otherwise
 * the default. Blocked or broken storage never throws (it gives the default).
 */
export function initialTab(search: string, store: TabStore | null = localStore()): TabId {
  const fromLink = new URLSearchParams(search).get(TAB_PARAM)
  if (isTab(fromLink)) return fromLink
  try {
    const remembered = store?.getItem(TAB_STORAGE_KEY) ?? null
    return isTab(remembered) ? remembered : DEFAULT_TAB
  } catch {
    return DEFAULT_TAB
  }
}

/** Remembers the open tab for the next visit; a blocked storage is ignored. */
export function rememberTab(tab: TabId, store: TabStore | null = localStore()): void {
  try {
    store?.setItem(TAB_STORAGE_KEY, tab)
  } catch {
    // Without storage the next visit opens the default tab.
  }
}
