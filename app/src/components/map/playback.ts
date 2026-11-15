import { useEffect, useState } from 'react'

/** One month per this many milliseconds while the time-lapse plays. */
export const PLAY_INTERVAL_MS = 1200

/** The index to show after `index`, or null at the end (the time-lapse then pauses). */
export function nextPlayIndex(index: number, count: number): number | null {
  return index >= 0 && index < count - 1 ? index + 1 : null
}

/** Where pressing Play starts: from the first month when the current one is the last (or unknown). */
export function playStartIndex(index: number, count: number): number {
  return index < 0 || index >= count - 1 ? 0 : index
}

export function prefersReducedMotion(): boolean {
  return typeof window !== 'undefined' && typeof window.matchMedia === 'function' && window.matchMedia('(prefers-reduced-motion: reduce)').matches
}

/** True while the system asks for reduced motion (follows a change of the setting). */
export function useReducedMotion(): boolean {
  const [reduced, setReduced] = useState(prefersReducedMotion)
  useEffect(() => {
    if (typeof window === 'undefined' || typeof window.matchMedia !== 'function') return
    const query = window.matchMedia('(prefers-reduced-motion: reduce)')
    const on = () => setReduced(query.matches)
    query.addEventListener('change', on)
    return () => query.removeEventListener('change', on)
  }, [])
  return reduced
}
