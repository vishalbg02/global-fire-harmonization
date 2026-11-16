import { useRef, useState } from 'react'
import * as UI from '../../content/ui.ts'
import { showToast } from '../common/toastStore.ts'
import { Button } from '../ui/Button.tsx'
import { copyAndConfirm } from './copyLink.ts'

/**
 * Copies the address of the current view; the toast confirms it ("Link copied"). If copying is not possible, the
 * button's own status line says so and the link is shown selected, to copy by hand.
 */
export function CopyLinkButton({ notify = showToast }: { notify?: (message: string) => void }) {
  const [state, setState] = useState<'idle' | 'copied' | 'manual'>('idle')
  const box = useRef<HTMLInputElement>(null)
  const href = typeof window === 'undefined' ? '' : window.location.href
  const onClick = async () => {
    const ok = await copyAndConfirm(window.location.href, notify)
    setState(ok ? 'copied' : 'manual')
    if (!ok) setTimeout(() => box.current?.select(), 0)
  }
  return (
    <div className="copy-link">
      <Button onClick={() => void onClick()}>{UI.COPY_LINK}</Button>
      {/* The success is read out once, by the toast; a failure is read out here, with the link below. */}
      <span role="status" aria-live="polite" className="visually-hidden">
        {state === 'manual' ? UI.LINK_COPY_FAILED : ''}
      </span>
      {state === 'manual' && (
        <input ref={box} className="copy-fallback" readOnly aria-label={UI.COPY_LINK} defaultValue={href} onFocus={(e) => e.target.select()} />
      )}
    </div>
  )
}
