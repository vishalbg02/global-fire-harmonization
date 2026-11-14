import type { RefObject } from 'react'
import { useQuery } from '@tanstack/react-query'
import { ApiError, fetchEvidence } from '../../api/client.ts'
import type { EntityEvidence, MapCell, Metadata } from '../../api/contract.ts'
import { evidenceFromEntityMonth } from '../../api/contract.ts'
import { bboxLabel } from '../../state/bbox.ts'
import { monthLabel } from '../../state/months.ts'
import type { Area } from '../../state/selection.ts'
import { useAreaSeries } from '../area/useAreaSeries.ts'
import { EmptyState, ErrorState, LoadingState } from '../common/States.tsx'
import { EvidenceBody } from './EvidenceBody.tsx'

export const CELL_HEADING = 'Cell (no per-satellite breakdown)'

/** The selected map cell and its record for the selected month (null while it loads). */
export interface SelectedCell {
  id: string
  record: MapCell | null
  loading: boolean
}

interface Props {
  area: Area
  month: { year: number; month: number } | null
  cell: SelectedCell | null
  meta: Metadata | null
  /** The heading is the focus target when a calendar cell is clicked. */
  headingRef: RefObject<HTMLHeadingElement | null>
  onShowWorld: () => void
}

export function AreaNotFound({
  area,
  month,
  onShowWorld,
}: {
  area: Area
  month: { year: number; month: number }
  onShowWorld: () => void
}) {
  return (
    <div className="state state-error" role="alert">
      <p>{`Area not found: ${area.entity_name}. There is no evidence record for it in ${monthLabel(month)}.`}</p>
      {area.entity_type !== 'GLOBAL' && (
        <button type="button" onClick={onShowWorld}>
          Show the world
        </button>
      )}
    </div>
  )
}

/**
 * The evidence and uncertainty panel (T-036). For a selected map cell it shows the cell's map
 * record; otherwise it shows the evidence of the calendar's area for the selected month.
 */
export function EvidencePanel({ area, month, cell, meta, headingRef, onShowWorld }: Props) {
  const custom = area.entity_type === 'CUSTOM'
  // GET /api/evidence does not serve a custom area: its evidence is the month's record of the
  // series returned by the custom call (the same query the calendar uses).
  const areaQuery = useQuery({
    queryKey: ['evidence', area.entity_type, area.entity_id, month?.year, month?.month],
    queryFn: () => fetchEvidence(area.entity_type as 'COUNTRY' | 'CONTINENT' | 'GLOBAL', area.entity_id, month!.year, month!.month),
    enabled: cell === null && month !== null && !custom,
    retry: false,
  })
  const customSeries = useAreaSeries(area, { enabled: cell === null && month !== null && custom })
  let customEvidence: EntityEvidence | null = null
  let customEvidenceError: string | null = null
  if (custom && month !== null && customSeries.data !== undefined) {
    const record = customSeries.data.find((r) => r.year === month.year && r.month === month.month)
    try {
      customEvidence = record === undefined ? null : evidenceFromEntityMonth(record)
    } catch {
      customEvidenceError = 'The custom area record could not be read.'
    }
  }
  const customApiError = custom && customSeries.error instanceof ApiError ? customSeries.error : null

  const when = month === null ? '' : monthLabel(month)
  const heading = cell !== null ? CELL_HEADING : `Evidence: ${area.entity_name}${when === '' ? '' : `, ${when}`}`
  const notFound = !custom && areaQuery.error instanceof ApiError && areaQuery.error.status === 404

  return (
    <section className="evidence-panel" aria-label="Evidence and uncertainty">
      <h2 ref={headingRef} tabIndex={-1}>
        {heading}
      </h2>
      {cell !== null && (
        <p className="evidence-subject">{`${cell.id}${when === '' ? '' : `, ${when}`}`}</p>
      )}
      {cell === null && area.entity_type === 'CUSTOM' && (
        <p className="evidence-subject">{bboxLabel(area.bbox)}</p>
      )}

      {month === null && cell === null && <EmptyState message="Choose a month to see the evidence." />}

      {cell !== null && cell.loading && <LoadingState what="the cell" />}
      {cell !== null && !cell.loading && cell.record === null && (
        <EmptyState message="This cell has no record for this month." />
      )}
      {cell !== null && cell.record !== null && (
        <EvidenceBody record={cell.record} contractVersion={meta?.contract_version ?? null} />
      )}

      {cell === null && month !== null && !custom && areaQuery.isPending && <LoadingState what="the evidence" />}
      {cell === null && month !== null && !custom && areaQuery.isError && notFound && (
        <AreaNotFound area={area} month={month} onShowWorld={onShowWorld} />
      )}
      {cell === null && !custom && areaQuery.isError && !notFound && (
        <ErrorState
          message="Data are not available right now. The evidence could not be loaded."
          onRetry={() => void areaQuery.refetch()}
        />
      )}
      {cell === null && !custom && areaQuery.data !== undefined && (
        <EvidenceBody
          record={areaQuery.data}
          rawByWitness={areaQuery.data.raw_by_witness}
          contractVersion={meta?.contract_version ?? null}
        />
      )}

      {cell === null && month !== null && custom && customSeries.isPending && <LoadingState what="the evidence" />}
      {cell === null && custom && customSeries.isError && (
        <ErrorState
          message={customApiError?.detail ?? 'Data are not available right now. The evidence could not be loaded.'}
          onRetry={customApiError?.status === 422 ? undefined : () => void customSeries.refetch()}
        />
      )}
      {cell === null && month !== null && custom && customSeries.data !== undefined && customEvidenceError !== null && (
        <ErrorState message={customEvidenceError} onRetry={() => void customSeries.refetch()} />
      )}
      {cell === null && month !== null && custom && customSeries.data !== undefined && customEvidenceError === null && customEvidence === null && (
        <EmptyState message={`The custom area has no record for ${when}.`} />
      )}
      {cell === null && custom && customEvidence !== null && (
        <EvidenceBody
          record={customEvidence}
          rawByWitness={customEvidence.raw_by_witness}
          contractVersion={meta?.contract_version ?? null}
        />
      )}
    </section>
  )
}
