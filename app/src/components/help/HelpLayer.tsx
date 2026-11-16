import { useCallback, useEffect, useLayoutEffect, useRef } from 'react'
import type { ShortcutId } from '../../content/help.ts'
import { rememberTourDismissed } from '../../state/howto.ts'
import { HELP_BUTTON_ID } from '../layout/Header.tsx'
import { returnFocusTarget } from './focusTrap.ts'
import { GlobeHint } from './GlobeHint.tsx'
import { HelpSheet } from './HelpSheet.tsx'
import { ShortcutsSheet } from './ShortcutsSheet.tsx'
import { shortcutFor } from './shortcuts.ts'
import type { KeyTarget } from './shortcuts.ts'
import { Tour } from './Tour.tsx'

/** What the help layer shows: the guided tour, the Help sheet, the shortcuts sheet, or nothing. */
export type HelpMode = 'tour' | 'sheet' | 'shortcuts' | null

/** What the keyboard shortcuts and the tour can do in the app. */
export interface HelpActions {
  stepMonth: (delta: -1 | 1) => void
  stepYear: (delta: -1 | 1) => void
  togglePlay: () => void
  toggleGlobe: () => void
  toggleSatellite: () => void
  focusSearch: () => void
}

export interface HelpLayerProps {
  mode: HelpMode
  onMode: (mode: HelpMode) => void
  actions: HelpActions
  /** The map shape now, for the hint shown the first time the globe is chosen. */
  shape: 'flat' | 'globe'
  /** Opens the methods page inside the app (the Help sheet's link). */
  onOpenMethods?: () => void
}

/** Runs one shortcut. Esc closes the help; the others act on the map page. */
function run(id: ShortcutId, p: HelpLayerProps): boolean {
  const a = p.actions
  switch (id) {
    case 'month-prev':
      a.stepMonth(-1)
      return true
    case 'month-next':
      a.stepMonth(1)
      return true
    case 'year-prev':
      a.stepYear(-1)
      return true
    case 'year-next':
      a.stepYear(1)
      return true
    case 'play':
      a.togglePlay()
      return true
    case 'globe':
      a.toggleGlobe()
      return true
    case 'satellite':
      a.toggleSatellite()
      return true
    case 'search':
      a.focusSearch()
      return true
    case 'shortcuts':
      p.onMode(p.mode === 'shortcuts' ? null : 'shortcuts')
      return true
    case 'close':
      if (p.mode === null) return false
      p.onMode(null)
      return true
  }
}

/**
 * The guided tour, the Help sheet, the shortcuts sheet, the keyboard shortcuts (one listener for the page) and the
 * one-line globe hint. Focus goes back to the control that opened the help when it closes, else to the Help button.
 */
export function HelpLayer(props: HelpLayerProps) {
  const { mode, onMode, shape, onOpenMethods } = props
  const latest = useRef(props)
  useLayoutEffect(() => {
    latest.current = props
  })

  // Remember who opened the help, store the tour's dismissal, and hand focus back on close.
  const opener = useRef<Element | null>(null)
  const prevMode = useRef<HelpMode>(mode)
  useLayoutEffect(() => {
    const prev = prevMode.current
    prevMode.current = mode
    if (prev === mode) return
    if (prev === null) opener.current = document.activeElement
    if (prev === 'tour') rememberTourDismissed()
    if (mode === null) {
      const to = returnFocusTarget(opener.current, document.getElementById(HELP_BUTTON_ID), document)
      opener.current = null
      if (to instanceof HTMLElement) to.focus({ preventScroll: true })
    }
  }, [mode])

  // One keydown listener for the whole page.
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const target = e.target instanceof Element ? (e.target as unknown as KeyTarget) : null
      const id = shortcutFor({ key: e.key, ctrlKey: e.ctrlKey, metaKey: e.metaKey, altKey: e.altKey, defaultPrevented: e.defaultPrevented, target })
      if (id === null) return
      // While the help is open, only Esc and "?" act: the other keys belong to the page behind it.
      const p = latest.current
      if (p.mode !== null && id !== 'close' && id !== 'shortcuts') return
      if (run(id, p)) e.preventDefault()
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [])

  const close = useCallback(() => onMode(null), [onMode])
  const toSheet = useCallback(() => onMode('sheet'), [onMode])

  return (
    <>
      {mode === 'tour' && <Tour onClose={close} onMoreHelp={toSheet} />}
      {mode === 'sheet' && (
        <HelpSheet onClose={close} onTour={() => onMode('tour')} onShortcuts={() => onMode('shortcuts')} onOpenMethods={onOpenMethods} />
      )}
      {mode === 'shortcuts' && <ShortcutsSheet onClose={close} />}
      <GlobeHint shape={shape} suppressed={mode === 'tour'} />
    </>
  )
}
