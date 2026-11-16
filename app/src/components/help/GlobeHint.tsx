import { useEffect, useRef, useState } from 'react'
import { createPortal } from 'react-dom'
import { globeHint } from '../../content/help.ts'
import { isGlobeHintShown, rememberGlobeHintShown } from '../../state/howto.ts'
import { isMacPlatform } from './shortcuts.ts'
import { globeHintDue } from './hints.ts'
import './help.css'

/** How long the hint stays on the map. */
export const GLOBE_HINT_MS = 5000

const platform = () => {
  if (typeof navigator === 'undefined') return ''
  const data = (navigator as Navigator & { userAgentData?: { platform?: string } }).userAgentData
  return data?.platform ?? navigator.platform ?? ''
}

/**
 * One quiet line on the map the first time the user turns it into a globe: how to turn and zoom it. Not on the
 * first-visit globe (the tour covers that), and only once per browser. It fades out after about five seconds.
 */
export function GlobeHint({ shape, suppressed }: { shape: 'flat' | 'globe'; suppressed: boolean }) {
  const prev = useRef(shape)
  const [shown, setShown] = useState(false)
  // The map's stage, found once the page is on screen; the live region sits in it from then on.
  const [stage, setStage] = useState<Element | null>(null)
  useEffect(() => {
    const frame = requestAnimationFrame(() => setStage(document.querySelector('.stage')))
    return () => cancelAnimationFrame(frame)
  }, [])

  useEffect(() => {
    const from = prev.current
    prev.current = shape
    if (!globeHintDue(from, shape, suppressed, isGlobeHintShown())) return
    rememberGlobeHintShown()
    setShown(true)
  }, [shape, suppressed])

  useEffect(() => {
    if (!shown) return
    const t = setTimeout(() => setShown(false), GLOBE_HINT_MS)
    return () => clearTimeout(t)
  }, [shown])

  if (stage === null) return null
  // The live region stays in the page, so the line is read out when it appears.
  return createPortal(
    <p className="help-hint" role="status" data-shown={shown}>
      {shown ? globeHint(isMacPlatform(platform())) : ''}
    </p>,
    stage,
  )
}
