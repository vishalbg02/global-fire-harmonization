import type { EntityMonth } from '../../api/contract.ts'
import { WITNESS_NAMES } from '../../content/witnesses.ts'
import { monthLabel, witnessSeries, witnessesPresent } from './series.ts'

const NO_DATA = 'no data'

function cell(value: number | null): string {
  return value === null ? NO_DATA : value.toFixed(1)
}

/** The same values as the chart, as a table: keyboard-operable and readable by screen readers. */
export function WitnessTable({ records, areaName }: { records: readonly EntityMonth[]; areaName: string }) {
  const witnesses = witnessesPresent(records)
  return (
    <div className="witness-table-wrap">
      <table className="witness-table">
        <caption>{`Monthly satellite-detected fire activity for ${areaName}`}</caption>
        <thead>
          <tr>
            <th scope="col">Month</th>
            <th scope="col">Harmonized estimate</th>
            <th scope="col">90% interval</th>
            <th scope="col">Baseline median</th>
            <th scope="col">Raw combined</th>
            {witnesses.map((w) => (
              <th key={w} scope="col">
                {WITNESS_NAMES[w]}
              </th>
            ))}
            <th scope="col">Notes</th>
          </tr>
        </thead>
        <tbody>
          {records.map((r) => (
            <tr key={monthLabel(r)}>
              <th scope="row">{monthLabel(r)}</th>
              <td>{cell(r.estimate)}</td>
              <td>
                {r.ci90_low === null || r.ci90_high === null ? NO_DATA : `${cell(r.ci90_low)} to ${cell(r.ci90_high)}`}
              </td>
              <td>{cell(r.baseline_median)}</td>
              <td>{r.raw_combined_cell_days}</td>
              {witnesses.map((w) => (
                <td key={w}>{cell(witnessSeries([r], w)[0])}</td>
              ))}
              <td>
                {[
                  r.reason_codes.includes('OUTAGE') ? 'Outage' : null,
                  r.reason_codes.includes('AQUA_DRIFT_ERA') ? 'Aqua drift era' : null,
                  r.data_level !== 'SP' ? 'Provisional' : null,
                ]
                  .filter((n): n is string => n !== null)
                  .join('; ') || '—'}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
