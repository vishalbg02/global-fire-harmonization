import { SHORTCUTS_NOTE, SHORTCUTS_TITLE, SHORTCUT_ROWS } from '../../content/help.ts'
import { HelpDialog } from './HelpDialog.tsx'

/** The keyboard shortcuts (the "?" key, or the link in the Help sheet): a small dialog, each key in a <kbd>. */
export function ShortcutsSheet({ onClose }: { onClose: () => void }) {
  return (
    <HelpDialog title={SHORTCUTS_TITLE} onClose={onClose} kind="small">
      <dl className="help-keys">
        {SHORTCUT_ROWS.map((row) => (
          <div key={row.label} className="help-keys-row">
            <dt>
              {row.keys.map((k, i) => (
                <span key={k}>
                  {i > 0 && <span className="help-keys-sep"> / </span>}
                  <kbd>{k}</kbd>
                </span>
              ))}
            </dt>
            <dd>{row.label}</dd>
          </div>
        ))}
      </dl>
      <p className="help-quiet">{SHORTCUTS_NOTE}</p>
    </HelpDialog>
  )
}
