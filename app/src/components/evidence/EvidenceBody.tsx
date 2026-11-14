import type { HarmonizedFields, Witness } from '../../api/contract.ts'
import { ACTIVITY_UNITS } from '../../content/calendar.ts'
import { NOT_AVAILABLE_YET, isRawOnlyRecord, useRawOnly } from '../../content/rawOnly.ts'
import { methodsHref } from '../../content/methodsLink.ts'
import { REASON_TEXTS } from '../../content/reasonTexts.ts'
import { VERDICT_PRESENTATION } from '../../content/verdicts.ts'
import { WITNESS_NAMES } from '../../content/witnesses.ts'
import { NO_DATA, formatEstimate, formatPctOfNormal, verdictProbability } from '../map/format.ts'

export const PROVISIONAL_NOTICE = 'Provisional: may change when science-quality data arrive'
export const DISAGREEMENT_NOTE = 'Satellites disagree; uncertainty widened'

interface Props {
  record: HarmonizedFields
  /**
   * The raw contribution of each witness. `undefined` hides the section (a single cell has no
   * per-satellite breakdown); `null` means the record has none and says so.
   */
  rawByWitness?: Partial<Record<Witness, number>> | null
  /** From GET /api/meta; the record does not carry it. */
  contractVersion: string | null
}

/** The evidence for one month, as stored: nothing here is computed. */
export function EvidenceBody({ record, rawByWitness, contractVersion }: Props) {
  // A raw-only record (decided from the record, not from the global metadata): the harmonized
  // parts are not available yet, so no verdict or caveat is shown. A harmonized record is shown in full.
  const rawOnly = useRawOnly() && isRawOnlyRecord(record)
  const verdict = VERDICT_PRESENTATION[record.verdict]
  const probability = verdictProbability(record)
  const provisional = record.data_level !== 'SP'
  const rawEntries =
    rawByWitness === undefined || rawByWitness === null
      ? []
      : (Object.entries(rawByWitness) as [Witness, number][])
  return (
    <div className="evidence-body">
      <section aria-labelledby="ev-verdict">
        <h3 id="ev-verdict">Verdict</h3>
        {rawOnly ? (
          <p className="evidence-verdict">Not available yet</p>
        ) : (
          <>
            <p className="evidence-verdict">
              <span aria-hidden="true">{`${verdict.icon} `}</span>
              {verdict.label}
            </p>
            {probability !== null && <p>{probability}</p>}
            <p className="evidence-note">{verdict.description}</p>
          </>
        )}
        {rawOnly && <p className="evidence-note">{NOT_AVAILABLE_YET}</p>}
        {provisional && <p className="evidence-provisional">{PROVISIONAL_NOTICE}</p>}
      </section>

      <section aria-labelledby="ev-numbers">
        <h3 id="ev-numbers">Numbers</h3>
        <dl>
          <dt>Compared with normal</dt>
          <dd>{rawOnly ? 'Not available yet' : formatPctOfNormal(record.pct_of_normal)}</dd>
          <dt>Harmonized estimate</dt>
          <dd>
            {record.estimate === null
              ? rawOnly
                ? 'Not available yet'
                : NO_DATA
              : `${formatEstimate(record)} (${ACTIVITY_UNITS})`}
          </dd>
        </dl>
      </section>

      {!rawOnly && (
      <section aria-labelledby="ev-witnesses">
        <h3 id="ev-witnesses">Satellites used</h3>
        {record.witnesses_used.length === 0 ? (
          <p>No satellite contributed usable data.</p>
        ) : (
          <ul>
            {record.witnesses_used.map((w) => (
              <li key={w}>{WITNESS_NAMES[w]}</li>
            ))}
          </ul>
        )}
        {record.disagreement_scale !== null && record.disagreement_scale > 1 && (
          <p className="evidence-note">
            {`${DISAGREEMENT_NOTE} (disagreement scale ${record.disagreement_scale.toFixed(2)}).`}
          </p>
        )}
      </section>
      )}

      {rawByWitness !== undefined && (
        <section aria-labelledby="ev-raw">
          <h3 id="ev-raw">Raw contribution of each satellite</h3>
          {rawEntries.length === 0 ? (
            <p>{NO_DATA}</p>
          ) : (
            <ul>
              {rawEntries.map(([witness, value]) => (
                <li key={witness}>{`${WITNESS_NAMES[witness]}: ${value}`}</li>
              ))}
            </ul>
          )}
          <p className="evidence-note">
            Fire-active cell-days, raw: not harmonized, so not comparable between satellites.
          </p>
        </section>
      )}

      {(!rawOnly || record.reason_codes.length > 0) && (
      <section aria-labelledby="ev-reasons">
        <h3 id="ev-reasons">Why</h3>
        {record.reason_codes.length === 0 ? (
          <p>No caveats are recorded for this month.</p>
        ) : (
          <ul className="evidence-reasons">
            {record.reason_codes.map((code) => (
              <li key={code}>
                {REASON_TEXTS[code]} <small className="reason-code">{code}</small>{' '}
                <a className="learn-more" href={methodsHref(`reason-${code}`)}>
                  Learn more
                </a>
              </li>
            ))}
          </ul>
        )}
      </section>
      )}

      <p className="evidence-versions">
        {`Method version: ${record.method_version}`}
        {contractVersion !== null && ` · Contract version: ${contractVersion}`}
      </p>
    </div>
  )
}
