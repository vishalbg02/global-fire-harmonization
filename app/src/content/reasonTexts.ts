import type { ReasonCode } from '../api/contract.ts'

/**
 * Plain-language text for every reason code (the evidence panel, T-036).
 *
 * Approved by the Lead on PR #28: the nine drafts of the workstream prompt section 11 as
 * written, and the replacement text for DIURNAL_CAVEAT. Any change needs the Lead's approval.
 */
export const REASON_TEXTS: Record<ReasonCode, string> = {
  OUTAGE: "Satellite data were missing for part of this month, so it can't be judged reliably.",
  INSUFFICIENT_BASELINE: 'There is too little historical fire activity here to define what is normal.',
  INSUFFICIENT_OVERLAP:
    "There weren't enough months when the satellites overlapped here to calibrate them reliably.",
  WITNESS_DISAGREEMENT: 'The satellites disagree more than expected, so the uncertainty was widened.',
  WIDE_INTERVAL: 'The uncertainty range is too wide for a confident verdict.',
  PROVISIONAL_NRT: 'Based on near-real-time data; values may change when science-quality data arrive.',
  AQUA_DRIFT_ERA: "Aqua MODIS's orbit has drifted, so it is not used as a witness for this period.",
  SINGLE_WITNESS: 'Only one satellite contributed this month.',
  POOLED_CALIBRATION: 'Local data were sparse, so calibration borrows from the wider region.',
  DIURNAL_CAVEAT:
    'Satellites pass over at fixed times of day. Fires that burn mainly at other hours can be under-counted, and differently by each satellite.',
}
