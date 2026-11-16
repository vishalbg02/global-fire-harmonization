import { GLOSSARY, HOW_TO_READ, HOW_TO_READ_TITLE } from '../../content/plainLanguage.ts'
import { VERDICTS } from '../../api/contract.ts'
import { methodsHref } from '../../content/methodsLink.ts'
import * as UI from '../../content/ui.ts'
import { VERDICT_PRESENTATION } from '../../content/verdicts.ts'
import { Button } from '../ui/Button.tsx'

interface Props {
  /** The close button of the old panel; left out inside the Help sheet, which has its own Close. */
  onClose?: () => void
  onEscape?: () => void
  /** 'sheet': inside the Help sheet (T-093), one column; 'panel': the earlier panel's look. */
  variant?: 'panel' | 'sheet'
}

/**
 * "How to read this": the approved steps and glossary of plainLanguage.ts and the verdict descriptions, word for word.
 * Since T-093 it is shown inside the Help sheet, never as a panel over the map.
 */
export function HowToRead({ onClose, onEscape, variant = 'panel' }: Props) {
  return (
    <section
      id="how-to-read"
      className={variant === 'sheet' ? 'help-howto' : 'how-to-read'}
      aria-label={HOW_TO_READ_TITLE}
      onKeyDown={(e) => {
        // Esc closes the panel for now; only the button remembers it as dismissed.
        if (e.key === 'Escape' && onEscape !== undefined) onEscape()
      }}
    >
      <div className="how-head">
        {variant === 'sheet' ? <h3>{HOW_TO_READ_TITLE}</h3> : <h2>{HOW_TO_READ_TITLE}</h2>}
        {onClose !== undefined && <Button onClick={onClose}>{UI.HOW_TO_READ_CLOSE}</Button>}
      </div>
      <ol className="how-steps">
        {HOW_TO_READ.map((s) => (
          <li key={s.id}>
            <strong>{s.title}.</strong> {s.text}
          </li>
        ))}
      </ol>
      <p>{UI.HOW_TO_READ_VERDICTS}</p>
      <ul>
        {VERDICTS.map((v) => (
          <li key={v}>
            <strong>{`${VERDICT_PRESENTATION[v].icon} ${VERDICT_PRESENTATION[v].label}.`}</strong> {VERDICT_PRESENTATION[v].description}
          </li>
        ))}
      </ul>
      <details>
        <summary>{UI.HOW_TO_READ_GLOSSARY}</summary>
        <dl className="glossary">
          {GLOSSARY.map((g) => (
            <div key={g.id}>
              <dt>{g.term}</dt>
              <dd>{g.hint}</dd>
            </div>
          ))}
        </dl>
      </details>
      <p>
        <a href={methodsHref('baseline-verdicts')}>{UI.HOW_TO_READ_MORE}</a>
      </p>
    </section>
  )
}
