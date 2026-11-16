import { useEffect } from 'react'
import { useQuery } from '@tanstack/react-query'
import { fetchMeta, fetchValidation } from '../../api/client.ts'
import { REASON_CODES } from '../../api/contract.ts'
import { ErrorState, LoadingState } from '../common/States.tsx'
import {
  DATASET_DOIS,
  GRID_EVIDENCE,
  GRID_EVIDENCE_CONSEQUENCES,
  GRID_EVIDENCE_SOURCE,
  METHOD_SECTIONS,
  PLANNED_TESTS,
  PLANNED_TESTS_NOTE,
  REFERENCES,
} from '../../content/methods.ts'
import { IN_PLAIN_WORDS, IN_PLAIN_WORDS_TITLE } from '../../content/plainLanguage.ts'
import { REASON_CODE_SHORT } from '../../content/reasonCodes.ts'
import { REASON_TEXTS } from '../../content/reasonTexts.ts'
import { VERDICT_PRESENTATION } from '../../content/verdicts.ts'
import { VERDICTS } from '../../api/contract.ts'
import { hashTarget, reasonAnchor } from '../../content/methodsLink.ts'
import { ValidationResultsView } from './ValidationResultsView.tsx'
import './methodsPage.css'

/**
 * Ids of the sections of this page. A method section whose own id is one of these gets no alias anchor (T-089).
 */
const PAGE_SECTION_IDS: ReadonlySet<string> = new Set(['plain-words', 'validation', 'method', 'verdicts', 'reason-codes', 'grid', 'planned-tests', 'sources'])

/** Scrolls to the element the address's hash names, opening any closed details around it. */
function scrollToHash(): void {
  const id = hashTarget(window.location.hash)
  if (id === null) return
  const el = document.getElementById(id)
  if (el === null) return
  for (let d = el.closest('details'); d !== null; d = d.parentElement?.closest('details') ?? null) d.open = true
  requestAnimationFrame(() => el.scrollIntoView({ block: 'start' }))
}

/**
 * The methods and validation page (T-041, redesigned in T-089): the method in plain language, the validation results
 * as the file holds them, what each verdict and reason code means, the grid evidence, and the
 * acknowledgement, dataset DOIs and references. Nothing here is computed.
 */
export function MethodsPage({ onBack }: { onBack: () => void }) {
  const validation = useQuery({ queryKey: ['validation'], queryFn: () => fetchValidation(), retry: false })
  const meta = useQuery({ queryKey: ['meta'], queryFn: () => fetchMeta(), retry: false })
  // A link such as "Learn more" opens this page at an anchor. The page is loaded after the address is read, so the
  // browser cannot scroll there by itself: scroll once it is drawn, and again when the validation results above have
  // loaded and moved it (T-093).
  const validationSettled = validation.isSuccess || validation.isError
  useEffect(() => scrollToHash(), [validationSettled])
  useEffect(() => {
    const onHash = () => scrollToHash()
    window.addEventListener('hashchange', onHash)
    return () => window.removeEventListener('hashchange', onHash)
  }, [])

  return (
    <main id="main-content" tabIndex={-1} className="methods-page">
      <nav aria-label="Methods page">
        <button type="button" onClick={onBack}>
          Back to the map
        </button>
        <ul className="methods-toc">
          <li><a href="#plain-words">In plain words</a></li>
          <li><a href="#validation">Validation results</a></li>
          <li><a href="#method">Method</a></li>
          <li><a href="#verdicts">Verdicts</a></li>
          <li><a href="#reason-codes">Reason codes</a></li>
          <li><a href="#grid">Grid evidence</a></li>
          <li><a href="#planned-tests">Test plan</a></li>
          <li><a href="#sources">Sources and references</a></li>
        </ul>
      </nav>

      <h2>Methods and validation</h2>

      <section aria-labelledby="plain-words">
        <h3 id="plain-words">{IN_PLAIN_WORDS_TITLE}</h3>
        {IN_PLAIN_WORDS.map((p) => (
          <p key={p} className="plain-words">
            {p}
          </p>
        ))}
      </section>

      <section aria-labelledby="validation">
        <h3 id="validation">Validation results</h3>
        <p>
          Shown exactly as the results file holds them. Failures are shown as prominently as passes,
          and a test is only ever PASS if the file says so.
        </p>
        {validation.isPending && <LoadingState what="the validation results" />}
        {validation.isError && (
          <ErrorState
            message="The validation results are not available right now."
            onRetry={() => void validation.refetch()}
          />
        )}
        {validation.data !== undefined && <ValidationResultsView results={validation.data} />}
      </section>

      <section aria-labelledby="method">
        <h3 id="method">How the method works</h3>
        {METHOD_SECTIONS.map((section) => (
          <article key={section.id} id={`method-${section.id}`} className="method-section">
            {!PAGE_SECTION_IDS.has(section.id) && <span id={section.id} className="anchor-alias" />}
            <h4>{section.title}</h4>
            {section.paragraphs.map((p) => (
              <p key={p}>{p}</p>
            ))}
            <p className="method-meta">
              {section.labels.length > 0 && (
                <span className="method-labels">{section.labels.map((l) => `[${l}]`).join(' ')} </span>
              )}
              <span>{`Source: ${section.source}`}</span>
            </p>
          </article>
        ))}
      </section>

      <section aria-labelledby="verdicts">
        <h3 id="verdicts">What each verdict means</h3>
        <dl>
          {VERDICTS.map((v) => (
            <div key={v}>
              <dt>
                <span aria-hidden="true">{`${VERDICT_PRESENTATION[v].icon} `}</span>
                {VERDICT_PRESENTATION[v].label}
              </dt>
              <dd>{VERDICT_PRESENTATION[v].description}</dd>
            </div>
          ))}
        </dl>
      </section>

      <section aria-labelledby="reason-codes">
        <h3 id="reason-codes">Reason codes</h3>
        <dl>
          {REASON_CODES.map((code) => (
            <div key={code} id={reasonAnchor(code)} className="reason-entry">
              <dt>
                {REASON_CODE_SHORT[code]} <small className="reason-code">{code}</small>
              </dt>
              <dd>{REASON_TEXTS[code]}</dd>
            </div>
          ))}
        </dl>
      </section>

      <section aria-labelledby="grid">
        <h3 id="grid">Why this grid (D-009)</h3>
        <table>
          <caption>Aqua against S-NPP agreement on 2012 to 2016, by grid size</caption>
          <thead>
            <tr>
              <th scope="col">Fine cell</th>
              <th scope="col">Analysis cell</th>
              <th scope="col">Spearman</th>
              <th scope="col">Both above 0</th>
              <th scope="col">Aqua at least 5 cell-days</th>
            </tr>
          </thead>
          <tbody>
            {GRID_EVIDENCE.map((row) => (
              <tr key={`${row.fine}-${row.analysis}`}>
                <td>{row.fine}</td>
                <td>{row.chosen ? `${row.analysis} (chosen)` : row.analysis}</td>
                <td>{row.spearman}</td>
                <td>{row.bothPositive}</td>
                <td>{row.aquaAtLeast5}</td>
              </tr>
            ))}
          </tbody>
        </table>
        <ul>
          {GRID_EVIDENCE_CONSEQUENCES.map((c) => (
            <li key={c}>{c}</li>
          ))}
        </ul>
        <p className="method-meta">{`Source: ${GRID_EVIDENCE_SOURCE}`}</p>
      </section>

      <section aria-labelledby="planned-tests" className="planned-tests">
        <h3 id="planned-tests">Test plan: the pass rules fixed in advance</h3>
        <p className="planned-note">{PLANNED_TESTS_NOTE}</p>
        <ul>
          {PLANNED_TESTS.map((t) => (
            <li key={t.id}>
              <strong>{`${t.id}: ${t.title}`}</strong>
              <p>{`Measures: ${t.measures}`}</p>
              <p>{`Planned pass rule: ${t.passRule}`}</p>
              <p>{`Applies to: ${t.appliesTo}`}</p>
            </li>
          ))}
        </ul>
      </section>

      <section aria-labelledby="sources">
        <h3 id="sources">Sources and references</h3>
        {meta.data !== undefined && <p className="acknowledgement">{meta.data.citation}</p>}
        <h4>NASA datasets (DOIs)</h4>
        <p>Standard (science-quality) products:</p>
        <ul>
          {DATASET_DOIS.standard.map((d) => (
            <li key={d.doi}>
              {`${d.name}: `}
              <a href={`https://doi.org/${d.doi}`}>{`doi:${d.doi}`}</a>
            </li>
          ))}
        </ul>
        <p>Near-real-time products (provisional):</p>
        <ul>
          {DATASET_DOIS.nearRealTime.map((d) => (
            <li key={d.doi}>
              {`${d.name}: `}
              <a href={`https://doi.org/${d.doi}`}>{`doi:${d.doi}`}</a>
            </li>
          ))}
        </ul>
        <h4>References</h4>
        <ul>
          {REFERENCES.map((r) => (
            <li key={r.text}>
              {`${r.text} `}
              {r.url !== '' && <a href={r.url}>{r.url}</a>}
            </li>
          ))}
        </ul>
      </section>
    </main>
  )
}
