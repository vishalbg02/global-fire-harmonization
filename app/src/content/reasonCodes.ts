import type { ReasonCode } from '../api/contract.ts'

// Short labels for the map tooltip only. The full plain-language reason texts are
// written and approved in T-036 (evidence panel); these are not those texts.
export const REASON_CODE_SHORT: Record<ReasonCode, string> = {
  OUTAGE: 'Data outage',
  INSUFFICIENT_BASELINE: 'Insufficient baseline',
  INSUFFICIENT_OVERLAP: 'Insufficient satellite overlap',
  WITNESS_DISAGREEMENT: 'Satellites disagree',
  WIDE_INTERVAL: 'Wide uncertainty',
  PROVISIONAL_NRT: 'Provisional data',
  AQUA_DRIFT_ERA: 'Aqua orbit drift period',
  SINGLE_WITNESS: 'Single satellite',
  POOLED_CALIBRATION: 'Pooled calibration',
  DIURNAL_CAVEAT: 'Overpass-time caveat',
  NOT_HARMONIZED: 'Raw data only',
}
