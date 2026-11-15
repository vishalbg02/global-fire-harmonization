import { useState } from 'react'
import { VERDICTS } from '../../api/contract.ts'
import { methodsHref } from '../../content/methodsLink.ts'
import * as UI from '../../content/ui.ts'
import { VERDICT_PRESENTATION } from '../../content/verdicts.ts'
import { Button } from '../ui/Button.tsx'

interface Props {
  /** True on the map page; the Methods link is left out on the methods page, as before. */
  showMethods: boolean
  onOpenMethods: () => void
}

/** The slim header: a text wordmark, one line of purpose, and the two links. */
export function Header({ showMethods, onOpenMethods }: Props) {
  const [help, setHelp] = useState(false)
  return (
    <header className="top">
      <div className="brand">
        <h1>{UI.WORDMARK}</h1>
        <p className="subtitle">{UI.TAGLINE}</p>
      </div>
      {showMethods && (
        <nav className="top-nav" aria-label="Help">
          <a
            className="top-link methods-link"
            href={methodsHref()}
            onClick={(e) => {
              e.preventDefault()
              onOpenMethods()
            }}
          >
            {UI.NAV_METHODS}
          </a>
          <button type="button" className="top-link" aria-expanded={help} aria-controls="how-to-read" onClick={() => setHelp((h) => !h)}>
            {UI.NAV_HOW_TO_READ}
          </button>
        </nav>
      )}
      {showMethods && help && (
        <section id="how-to-read" className="how-to-read" aria-label={UI.HOW_TO_READ_TITLE}>
          <p>{UI.HOW_TO_READ_INTRO}</p>
          <ul>
            {VERDICTS.map((v) => (
              <li key={v}>
                <strong>{`${VERDICT_PRESENTATION[v].icon} ${VERDICT_PRESENTATION[v].label}.`}</strong> {VERDICT_PRESENTATION[v].description}
              </li>
            ))}
          </ul>
          <p>
            <a href={methodsHref('baseline-verdicts')}>{UI.HOW_TO_READ_MORE}</a>
          </p>
          <Button onClick={() => setHelp(false)}>{UI.HOW_TO_READ_CLOSE}</Button>
        </section>
      )}
    </header>
  )
}
