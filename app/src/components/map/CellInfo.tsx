import type { MapCell } from '../../api/contract.ts'
import { REASON_CODE_SHORT } from '../../content/reasonCodes.ts'
import { VERDICT_PRESENTATION } from '../../content/verdicts.ts'
import { NO_DATA, formatEstimate, formatPctOfNormal, verdictProbability } from './format.ts'

/** Cell details: used for the hover tooltip and for the selected-cell panel. */
export function CellInfo({ cell }: { cell: MapCell }) {
  const verdict = VERDICT_PRESENTATION[cell.verdict]
  const probability = verdictProbability(cell)
  return (
    <dl className="cell-info">
      <dt>Cell</dt>
      <dd>{cell.cell_id}</dd>
      <dt>Verdict</dt>
      <dd>
        <span aria-hidden="true">{verdict.icon} </span>
        {verdict.label}
        {probability === null ? '' : `, ${probability}`}
      </dd>
      <dt>Compared with normal</dt>
      <dd>{formatPctOfNormal(cell.pct_of_normal)}</dd>
      <dt>Harmonized estimate (fire-active cell-days, Aqua-equivalent)</dt>
      <dd>{formatEstimate(cell)}</dd>
      <dt>Raw combined (fire-active cell-days)</dt>
      <dd>{cell.raw_combined_cell_days}</dd>
      <dt>Notes</dt>
      <dd>
        {cell.reason_codes.length === 0
          ? 'None'
          : cell.reason_codes.map((code) => REASON_CODE_SHORT[code]).join('; ')}
      </dd>
      {cell.data_level !== 'SP' && (
        <>
          <dt>Data level</dt>
          <dd>Provisional ({cell.data_level})</dd>
        </>
      )}
      {cell.estimate === null && cell.pct_of_normal === null && (
        <>
          <dt>Status</dt>
          <dd>{NO_DATA}</dd>
        </>
      )}
    </dl>
  )
}
