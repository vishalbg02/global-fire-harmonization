/** "How to read this" is shown open on the first visit and remembered as dismissed per browser (T-072). */
export const HOWTO_KEY = 'gfh.howto.dismissed'

/** True when the user dismissed the panel before. Storage can be blocked: then it is never "dismissed" and nothing throws. */
export function isHowToDismissed(): boolean {
  try {
    return window.localStorage.getItem(HOWTO_KEY) === '1'
  } catch {
    return false
  }
}

/** Remembers the dismissal in this browser only (no cookie, nothing sent anywhere). A blocked storage is ignored. */
export function rememberHowToDismissed(): void {
  try {
    window.localStorage.setItem(HOWTO_KEY, '1')
  } catch {
    // The page works without storage: the panel just opens again next time.
  }
}

/** First visit: no link parameters (a shared link goes straight to its view) and not dismissed before. */
export function howToOpenAtStart(search: string): boolean {
  return Array.from(new URLSearchParams(search).keys()).length === 0 && !isHowToDismissed()
}
