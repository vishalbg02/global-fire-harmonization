import {
  HELP_METHODS_LINK,
  HELP_SHEET_TITLE,
  HELP_SHORTCUTS_LINK,
  HELP_TAKE_TOUR,
  HELP_TAKE_TOUR_NOTE,
} from '../../content/help.ts'
import { methodsHref } from '../../content/methodsLink.ts'
import { HowToRead } from '../layout/HowToRead.tsx'
import { HelpDialog } from './HelpDialog.tsx'

export interface HelpSheetProps {
  onClose: () => void
  onTour: () => void
  onShortcuts: () => void
  /** Opens the methods page inside the app; without it the link is followed as an ordinary link. */
  onOpenMethods?: () => void
}

/**
 * The Help sheet (the Help button): the tour, the approved "How to read this" steps, verdicts and glossary word for word,
 * the keyboard shortcuts and the methods page.
 */
export function HelpSheet({ onClose, onTour, onShortcuts, onOpenMethods }: HelpSheetProps) {
  return (
    <HelpDialog title={HELP_SHEET_TITLE} onClose={onClose} kind="sheet">
      <div className="help-tour-row">
        <button type="button" className="btn btn-primary help-primary" onClick={onTour}>
          {HELP_TAKE_TOUR}
        </button>
        <span className="help-quiet">{HELP_TAKE_TOUR_NOTE}</span>
      </div>
      <HowToRead variant="sheet" />
      <ul className="help-links">
        <li>
          <button type="button" className="bare help-link" aria-haspopup="dialog" onClick={onShortcuts}>
            {HELP_SHORTCUTS_LINK}
          </button>
        </li>
        <li>
          <a
            className="help-link"
            href={methodsHref()}
            onClick={(e) => {
              if (onOpenMethods === undefined) return
              e.preventDefault()
              onClose()
              onOpenMethods()
            }}
          >
            {HELP_METHODS_LINK}
          </a>
        </li>
      </ul>
    </HelpDialog>
  )
}
