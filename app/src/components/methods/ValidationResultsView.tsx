import type { ValidationResults } from '../../api/contract.ts'
import { countStatuses, formatMeasured } from './validationFormat.ts'
import { NOT_MEASURED, NO_TESTS_RUN_MESSAGE, STATUS_COUNT_ORDER, TEST_STATUS_PRESENTATION } from '../../content/testStatus.ts'

/**
 * The validation results exactly as the file holds them: in file order, every status as text
 * plus an icon, nothing computed or restyled. An empty list says no test has been run.
 */
export function ValidationResultsView({ results }: { results: ValidationResults }) {
  const counts = countStatuses(results.tests)
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
          <ol className="validation-tests">
            {results.tests.map((t) => {
              const status = TEST_STATUS_PRESENTATION[t.status]
              return (
                <li key={t.test_id} className={`validation-test status-${t.status.toLowerCase()}`}>
                  <h4>
                    <span className="status-badge">
                      <span aria-hidden="true">{`${status.icon} `}</span>
                      {status.label}
                    </span>
                    {` ${t.title}`}
                  </h4>
                  <p className="test-id">{`${t.test_id} · family ${t.family}`}</p>
                  <dl>
                    <dt>Case</dt>
                    <dd>{t.case}</dd>
                    <dt>Pass rule</dt>
                    <dd>{t.criterion}</dd>
                    <dt>Threshold</dt>
                    <dd>{t.threshold}</dd>
                    <dt>Measured</dt>
                    <dd>
                      {Object.keys(t.measured).length === 0 ? (
                        NOT_MEASURED
                      ) : (
                        <ul>
                          {Object.entries(t.measured).map(([key, value]) => (
                            <li key={key}>{`${key}: ${formatMeasured(value)}`}</li>
                          ))}
                        </ul>
                      )}
                    </dd>
                    {t.notes !== '' && (
                      <>
                        <dt>Notes</dt>
                        <dd>{t.notes}</dd>
                      </>
                    )}
                  </dl>
                </li>
              )
            })}
          </ol>
        </>
      )}
    </div>
  )
}
