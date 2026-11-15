import { methodsHref } from '../../content/methodsLink.ts'
import * as UI from '../../content/ui.ts'

/** The id of the Help button: focus goes back to it when the help closes. */
export const HELP_BUTTON_ID = 'help-button'
/** Kept for the callers that still use the earlier name. */
export const HOW_TO_TOGGLE_ID = HELP_BUTTON_ID

interface Props {
  /** True on the map page; the Methods link is left out on the methods page, as before. */
  showMethods: boolean
  onOpenMethods: () => void
  /** Whether the help (the tour, the Help sheet or the shortcuts) is open. */
  helpOpen?: boolean
  onHelp?: () => void
}

/** The slim header: a text wordmark, one line of purpose, "Methods and validation" and "Help". */
export function Header({ showMethods, onOpenMethods, helpOpen = false, onHelp = () => {} }: Props) {
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
          <button type="button" id={HELP_BUTTON_ID} className="top-link" aria-haspopup="dialog" aria-expanded={helpOpen} onClick={onHelp}>
            {UI.NAV_HELP}
          </button>
        </nav>
      )}
    </header>
  )
}
