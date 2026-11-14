import type { Source } from '../state/selection.ts'

export const SOURCE_LABELS: Record<Source, string> = {
  raw: 'Raw',
  harmonized: 'Harmonized',
}

// Approved by the Lead (T-033 review).
export const RAW_DESCRIPTION =
  'Raw: fire-active cell-days summed across all operating satellites (raw_combined_cell_days). Not comparable across years, because the number of satellites changes.'

export const HARMONIZED_DESCRIPTION = 'Harmonized: fire-active cell-days, Aqua-equivalent.'

/** Shown next to the control while Raw is disabled; visible text, not a tooltip. */
export const RAW_UNAVAILABLE =
  'Raw is not available in % of normal mode: % of normal needs a baseline, which exists only for harmonized data. Choose Activity to see raw.'

/** One sentence on why raw counts jump (the Lead asked for it; the wording is to be approved). */
export const JUMP_CAPTION = 'Raw counts jump when satellites join or leave; harmonized values adjust for this.'
