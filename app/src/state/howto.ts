/**
 * First-visit help, remembered per browser (T-072, T-093). The guided tour opens on a first visit without link
 * parameters; once it is closed (Skip, Esc or finished) it stays closed. The key is the one "How to read this" used
 * before, so a returning visitor who dismissed that panel is not shown the tour either. Nothing is sent anywhere.
 */
export const HOWTO_KEY = 'gfh.howto.dismissed'
/** The key of the one-line hint shown the first time the user turns the map into a globe. */
export const GLOBE_HINT_KEY = 'gfh.hint.globe'

/** Reads a remembered flag. Storage can be blocked: then the flag is never set and nothing throws. */
export function readFlag(key: string): boolean {
  try {
    return window.localStorage.getItem(key) === '1'
  } catch {
    return false
  }
}

/** Remembers a flag in this browser only (no cookie). A blocked storage is ignored. */
export function writeFlag(key: string): void {
  try {
    window.localStorage.setItem(key, '1')
  } catch {
    // The page works without storage: the help just shows again next time.
  }
}

/** True when the user closed the first-visit help before. */
export function isHowToDismissed(): boolean {
  return readFlag(HOWTO_KEY)
}

/** Remembers that the first-visit help (the tour) was closed. */
export function rememberHowToDismissed(): void {
  writeFlag(HOWTO_KEY)
}

/** First visit: no link parameters (a shared link goes straight to its view) and not dismissed before. */
export function howToOpenAtStart(search: string): boolean {
  return Array.from(new URLSearchParams(search).keys()).length === 0 && !isHowToDismissed()
}

/** The tour's own names for the same rules. */
export const tourOpenAtStart = howToOpenAtStart
export const rememberTourDismissed = rememberHowToDismissed

/** Whether the globe hint was shown before, and remembering that it was. */
export const isGlobeHintShown = (): boolean => readFlag(GLOBE_HINT_KEY)
export const rememberGlobeHintShown = (): void => writeFlag(GLOBE_HINT_KEY)
