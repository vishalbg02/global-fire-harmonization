import { useSyncExternalStore } from 'react'

function mediaList(query: string): MediaQueryList | null {
  try {
    return typeof window !== 'undefined' && typeof window.matchMedia === 'function' ? window.matchMedia(query) : null
  } catch {
    return null
  }
}

/** True while the media query matches. False on the server and where matchMedia is missing (tests, old browsers). */
export function useMediaQuery(query: string): boolean {
  return useSyncExternalStore(
    (onChange) => {
      const list = mediaList(query)
      list?.addEventListener('change', onChange)
      return () => list?.removeEventListener('change', onChange)
    },
    () => mediaList(query)?.matches ?? false,
    () => false,
  )
}
