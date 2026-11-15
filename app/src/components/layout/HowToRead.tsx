import { GLOSSARY, HOW_TO_READ, HOW_TO_READ_TITLE } from '../../content/plainLanguage.ts'
import { VERDICTS } from '../../api/contract.ts'
import { methodsHref } from '../../content/methodsLink.ts'
import * as UI from '../../content/ui.ts'
import { VERDICT_PRESENTATION } from '../../content/verdicts.ts'
import { Button } from '../ui/Button.tsx'

/** The dismissible "How to read this": the steps and glossary of plainLanguage.ts and the verdict descriptions. */
export function HowToRead({ onClose }: { onClose: () => void }) {
  return (
    <section id="how-to-read" className="how-to-read" aria-label={HOW_TO_READ_TITLE}>
      <div className="how-head">
        <h2>{HOW_TO_READ_TITLE}</h2>
        <Button onClick={onClose}>{UI.HOW_TO_READ_CLOSE}</Button>
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
