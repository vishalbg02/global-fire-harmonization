import { useRef, useState } from 'react'
import * as UI from '../../content/ui.ts'
import { Button } from '../ui/Button.tsx'
import { copyText } from './copyLink.ts'

/** Copies the address of the current view. If copying is not possible, the link is shown selected to copy by hand. */
export function CopyLinkButton() {
  const [state, setState] = useState<'idle' | 'copied' | 'manual'>('idle')
  const box = useRef<HTMLInputElement>(null)
  const href = typeof window === 'undefined' ? '' : window.location.href
  const onClick = async () => {
    const ok = await copyText(window.location.href)
    setState(ok ? 'copied' : 'manual')
    if (!ok) setTimeout(() => box.current?.select(), 0)
  }
  return (
    <div className="copy-link">
      <Button onClick={() => void onClick()}>{UI.COPY_LINK}</Button>
      <span role="status" aria-live="polite" className={state === 'copied' ? 'copy-note' : 'visually-hidden'}>
        {state === 'copied' ? UI.LINK_COPIED : state === 'manual' ? UI.LINK_COPY_FAILED : ''}
      </span>
      {state === 'manual' && (
        <input ref={box} className="copy-fallback" readOnly aria-label={UI.COPY_LINK} defaultValue={href} onFocus={(e) => e.target.select()} />
      )}
    </div>
  )
}
