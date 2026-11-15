import { methodsHref } from '../../content/methodsLink.ts'
import * as UI from '../../content/ui.ts'

interface Props {
  /** True on the map page; the Methods link is left out on the methods page, as before. */
  showMethods: boolean
  onOpenMethods: () => void
  /** Whether the "How to read this" panel (rendered by the app under the header) is open. */
  howToOpen?: boolean
  onToggleHowTo?: () => void
}

/** The slim header: a text wordmark, one line of purpose, and the two links. */
export function Header({ showMethods, onOpenMethods, howToOpen = false, onToggleHowTo = () => {} }: Props) {
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
          <button type="button" className="top-link" aria-expanded={howToOpen} aria-controls="how-to-read" onClick={onToggleHowTo}>
            {UI.NAV_HOW_TO_READ}
          </button>
        </nav>
      )}
    </header>
  )
}
