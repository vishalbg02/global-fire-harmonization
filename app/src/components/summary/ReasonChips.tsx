import { useId, useState } from 'react'
import type { ReasonCode } from '../../api/contract.ts'
import { WHY_HEADING, WHY_LABEL } from '../../content/answer.ts'
import { NO_CAVEATS_TEXT } from '../../content/evidenceText.ts'
import { methodsHref, reasonAnchor } from '../../content/methodsLink.ts'
import { REASON_CODE_SHORT } from '../../content/reasonCodes.ts'
import { REASON_TEXTS } from '../../content/reasonTexts.ts'
import { SUMMARY_LEARN_MORE } from '../../content/ui.ts'
import { toggleReason } from './reasonChips.ts'

interface ChipProps {
  code: ReasonCode
  open: boolean
  onToggle: () => void
  idBase: string
}

/**
 * One stored reason code: the short label as a button, which opens the approved sentence (content/reasonTexts.ts) and
 * the "Learn more" link to its section of the methods page.
 */
export function ReasonChip({ code, open, onToggle, idBase }: ChipProps) {
  const bodyId = `${idBase}-${code}`
  return (
    <li className="reason-chip" data-open={open}>
      <button type="button" className="bare reason-chip-btn" aria-expanded={open} aria-controls={bodyId} onClick={onToggle}>
        <span className="reason-chip-mark" aria-hidden="true">
          {open ? '−' : '+'}
        </span>
        {REASON_CODE_SHORT[code]}
      </button>
      <p id={bodyId} className="reason-chip-text" hidden={!open}>
        {REASON_TEXTS[code]}{' '}
        <a className="learn-more" href={methodsHref(reasonAnchor(code))}>
          {SUMMARY_LEARN_MORE}
        </a>
      </p>
    </li>
  )
}

/**
 * "Why": every stored reason code of the month as a compact chip that expands to its sentence. With no code, the
 * approved "no caveat flags" sentence. `data-tour="why"` is the guided tour's anchor.
 */
export function ReasonChips({ codes, initialOpen = [] }: { codes: readonly ReasonCode[]; initialOpen?: readonly ReasonCode[] }) {
  const [open, setOpen] = useState<readonly ReasonCode[]>(initialOpen)
  const rawId = useId()
  const idBase = `why-${rawId.replace(/[^a-zA-Z0-9_-]/g, '')}`
  return (
    <section className="why" aria-label={WHY_LABEL} data-tour="why">
      <h3 className="why-heading">{WHY_HEADING}</h3>
      {codes.length === 0 ? (
        <p className="why-none">{NO_CAVEATS_TEXT}</p>
      ) : (
        <ul className="reason-chips">
          {codes.map((code) => (
            <ReasonChip key={code} code={code} idBase={idBase} open={open.includes(code)} onToggle={() => setOpen((o) => toggleReason(o, code))} />
          ))}
        </ul>
      )}
    </section>
  )
}
