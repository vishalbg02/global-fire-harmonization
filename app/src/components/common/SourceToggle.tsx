import { useId, useState } from 'react'
import { HARMONIZED_DESCRIPTION, JUMP_CAPTION, RAW_DESCRIPTION, RAW_UNAVAILABLE, SOURCE_LABELS } from '../../content/source.ts'
import { RAW_ONLY_HARMONIZED_UNAVAILABLE } from '../../content/rawOnly.ts'
import type { Source } from '../../state/selection.ts'
import { SegmentedControl } from '../ui/SegmentedControl.tsx'

const SOURCES: readonly Source[] = ['raw', 'harmonized']

interface Props {
  value: Source
  onChange: (source: Source) => void
  /** Raw is disabled while the calendar shows % of normal (the contract has no raw baseline). */
  rawDisabled: boolean
  /** True while only raw data exist (T-039): Harmonized is disabled with its reason written out. */
  harmonizedDisabled?: boolean
}

/**
 * The shared Raw / Harmonized control for the map and the calendar. A disabled option stays
 * in the tab order (`aria-disabled`) and its reason is written out, not hidden in a tooltip.
 * The descriptions sit in a collapsed "About this choice" line so the toolbar stays one row.
 */
export function SourceToggle({ value, onChange, rawDisabled, harmonizedDisabled = false }: Props) {
  const helpId = useId()
  // The reason Raw is unavailable is read out to screen readers at all times, and shown to everyone
  // when the user tries to choose Raw: it is not a standing notice above the map (T-039 review).
  const [triedRaw, setTriedRaw] = useState(false)
  const describedBy = rawDisabled ? `${helpId}-unavailable` : undefined
  return (
    <div className="source-toggle">
      <SegmentedControl<Source>
        legend="Data shown"
        name="data-source"
        value={value}
        onChange={(source) => {
          setTriedRaw(false)
          onChange(source)
        }}
        onDisabledChoice={(source) => setTriedRaw(source === 'raw')}
        options={SOURCES.map((source) => ({
          value: source,
          label: SOURCE_LABELS[source],
          disabled: source === 'raw' ? rawDisabled : harmonizedDisabled,
          describedBy,
        }))}
      />
      <details className="source-details">
        <summary>About this choice</summary>
        <p className="source-note" id={`${helpId}-description`}>
          {value === 'raw' ? RAW_DESCRIPTION : HARMONIZED_DESCRIPTION}
        </p>
        <p className="source-note source-caption">{JUMP_CAPTION}</p>
      </details>
      {harmonizedDisabled && <p className="source-note source-unavailable">{RAW_ONLY_HARMONIZED_UNAVAILABLE}</p>}
      {rawDisabled && (
        <p
          className={triedRaw ? 'source-note source-unavailable' : 'visually-hidden'}
          id={`${helpId}-unavailable`}
          role={triedRaw ? 'status' : undefined}
        >
          {RAW_UNAVAILABLE}
        </p>
      )}
    </div>
  )
}
