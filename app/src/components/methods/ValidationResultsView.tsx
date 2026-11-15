import { useState } from 'react'
import type { TestStatus, ValidationResults, ValidationTest } from '../../api/contract.ts'
import { NOT_MEASURED, NO_TESTS_RUN_MESSAGE, STATUS_COUNT_ORDER, TEST_STATUS_PRESENTATION } from '../../content/testStatus.ts'
import { FAMILY_RULE_TEXT, OVERVIEW_NOTE } from '../../content/validationText.ts'
import { countStatuses } from './validationFormat.ts'
import {
  type Family,
  type StatusFilter,
  filterTests,
  groupFamilies,
  measuredLabel,
  measuredText,
  officialSummary,
  startsOpen,
  testAnchor,
} from './validationModel.ts'
import './validationResults.css'

/** Measured lists longer than this start collapsed inside the detail (E1 stores 269 values). */
const MEASURED_INLINE_MAX = 12

function StatusBadge({ status }: { status: TestStatus }) {
  const p = TEST_STATUS_PRESENTATION[status]
  return (
    <span className="status-badge">
      <span aria-hidden="true">{`${p.icon} `}</span>
      {p.label}
    </span>
  )
}

function statusNote(family: Family): string {
  const counts = entryCountsText(family)
  if (family.statusFrom === 'entry') return `${counts}.`
  if (family.statusFrom === 'official') return `${counts}. Status: the official entry ${family.official?.test_id ?? ''} (${family.officialInfo?.source ?? ''}).`
  return `${counts}. Status: the worst of its entries (the file has no family-level entry).`
}

function entryCountsText(family: Family): string {
  const parts = STATUS_COUNT_ORDER.filter((s) => family.counts[s] > 0).map((s) => `${family.counts[s]} ${TEST_STATUS_PRESENTATION[s].label}`)
  return `${family.tests.length} ${family.tests.length === 1 ? 'entry' : 'entries'}: ${parts.join(', ')}`
}

function Measured({ test }: { test: ValidationTest }) {
  const entries = Object.entries(test.measured)
  if (entries.length === 0) return <>{NOT_MEASURED}</>
  const table = (
    <table className="measured-table">
      <tbody>
        {entries.map(([key, value]) => (
          <tr key={key}>
            <th scope="row" title={key}>
              {measuredLabel(key)}
            </th>
            <td>{measuredText(value, NOT_MEASURED)}</td>
          </tr>
        ))}
      </tbody>
    </table>
  )
  if (entries.length <= MEASURED_INLINE_MAX) return table
  return (
    <details className="measured-details">
      <summary>{`Measured values (${entries.length})`}</summary>
      {table}
    </details>
  )
}

/**
 * The validation results (T-089): the counts, one line per test family with its status, filter chips and one collapsible detail per
 * stored entry. A status is only ever one the file holds; a family without its own entry takes the worst status of its entries and
 * says so; failing and inconclusive entries start open so every failure and its notes are visible without a click; measured values
 * are shown exactly as stored.
 */
export function ValidationResultsView({ results }: { results: ValidationResults }) {
  const [filter, setFilter] = useState<StatusFilter>('ALL')
  const [opened, setOpened] = useState<ReadonlyMap<string, boolean>>(new Map())
  const counts = countStatuses(results.tests)
  const families = groupFamilies(results.tests)
  const shown = filterTests(results.tests, filter)
  const isOpen = (t: ValidationTest) => opened.get(t.test_id) ?? startsOpen(t.status)
  const setOpen = (id: string, open: boolean) => setOpened((m) => new Map(m).set(id, open))
  /** A link of the overview must land on an open detail that the filter does not hide. */
  const reveal = (id: string) => {
    setFilter('ALL')
    setOpen(id, true)
  }
  const chips: StatusFilter[] = ['ALL', ...STATUS_COUNT_ORDER.filter((s) => counts[s] > 0)]

  return (
    <div className="validation-results">
      {results.synthetic && (
        <p className="validation-synthetic" role="note">
          SYNTHETIC: these are example rows, not results.
        </p>
      )}
      <dl className="validation-file">
        <dt>Generated</dt>
        <dd>{results.generated_at}</dd>
        <dt>Method version</dt>
        <dd>{results.method_version}</dd>
        <dt>Contract version</dt>
        <dd>{results.contract_version}</dd>
        <dt>Synthetic</dt>
        <dd>{results.synthetic ? 'yes' : 'no'}</dd>
      </dl>
      {results.tests.length === 0 ? (
        <p className="state state-empty">{NO_TESTS_RUN_MESSAGE}</p>
      ) : (
        <>
          <ul className="validation-counts" aria-label="Number of tests by status">
            {STATUS_COUNT_ORDER.map((status) => (
              <li key={status} className={`status-${status.toLowerCase()}`}>
                <span aria-hidden="true">{`${TEST_STATUS_PRESENTATION[status].icon} `}</span>
                {`${TEST_STATUS_PRESENTATION[status].label}: ${counts[status]}`}
              </li>
            ))}
          </ul>

          <h4 id="results-overview">Results by test family</h4>
          <p className="overview-note">{OVERVIEW_NOTE}</p>
          <p className="overview-note">{FAMILY_RULE_TEXT}</p>
          <ol className="family-list" aria-labelledby="results-overview">
            {families.map((f) => (
              <li key={f.key} className={`family-row status-${f.status.toLowerCase()}`}>
                <a className="family-key" href={`#${testAnchor(f.anchorTestId)}`} onClick={() => reveal(f.anchorTestId)}>
                  {f.key}
                </a>
                <StatusBadge status={f.status} />
                <span className="family-meaning">{f.meaning}</span>
                {officialSummary(f) !== null && (
                  <span className="family-official">{`${f.status} ${officialSummary(f)}`}</span>
                )}
                <span className="family-counts">{statusNote(f)}</span>
                {f.official !== null && f.officialInfo !== null && (
                  <span className="family-reading">
                    {`${f.officialInfo.readingNote} Official entry ${f.official.test_id}: `}
                    {f.officialInfo.measuredKeys
                      .filter((k) => k in f.official!.measured)
                      .map((k) => `${measuredLabel(k).toLowerCase()} ${measuredText(f.official!.measured[k]!, NOT_MEASURED)}`)
                      .join('; ')}
                    .
                  </span>
                )}
                {f.separate.length > 0 && (
                  <ul className="family-separate" aria-label={`${f.key}: entries reported separately`}>
                    {f.separate.map((s) => (
                      <li key={s.test_id} className={`separate-row status-${s.status.toLowerCase()}`}>
                        <a className="family-key" href={`#${testAnchor(s.test_id)}`} onClick={() => reveal(s.test_id)}>
                          {s.test_id}
                        </a>
                        <StatusBadge status={s.status} />
                        <span className="family-meaning">{s.title}</span>
                      </li>
                    ))}
                  </ul>
                )}
              </li>
            ))}
          </ol>

          <h4 id="all-tests">All tests</h4>
          <div className="status-chips" role="group" aria-label="Filter the tests by status">
            {chips.map((c) => {
              const label = c === 'ALL' ? 'All' : TEST_STATUS_PRESENTATION[c].label
              const n = c === 'ALL' ? results.tests.length : counts[c]
              return (
                <button key={c} type="button" className={`chip chip-${c.toLowerCase()}`} aria-pressed={filter === c} onClick={() => setFilter(c)}>
                  {`${label} (${n})`}
                </button>
              )
            })}
          </div>
          <p className="overview-note" role="status">{`Showing ${shown.length} of ${results.tests.length} entries.`}</p>
          <ol className="validation-tests">
            {shown.map((t) => (
              <li key={t.test_id} id={testAnchor(t.test_id)} className={`validation-test status-${t.status.toLowerCase()}`}>
                <details open={isOpen(t)} onToggle={(e) => setOpen(t.test_id, e.currentTarget.open)}>
                  <summary>
                    <StatusBadge status={t.status} />
                    <span className="test-title">{` ${t.title}`}</span>
                    <span className="test-id">{`${t.test_id} · family ${t.family}`}</span>
                  </summary>
                  <dl>
                    {t.notes !== '' && (
                      <>
                        <dt>Notes</dt>
                        <dd>{t.notes}</dd>
                      </>
                    )}
                    <dt>Case</dt>
                    <dd>{t.case}</dd>
                    <dt>Pass rule</dt>
                    <dd>{t.criterion}</dd>
                    <dt>Threshold</dt>
                    <dd>{t.threshold}</dd>
                    <dt>Measured</dt>
                    <dd>
                      <Measured test={t} />
                    </dd>
                  </dl>
                </details>
              </li>
            ))}
          </ol>
        </>
      )}
    </div>
  )
}
