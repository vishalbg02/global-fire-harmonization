import { createContext, useContext } from 'react'
import type { Metadata, ReasonCode } from '../api/contract.ts'

/** The method version of a product set that has real raw counts but no harmonization yet. */
export const RAW_ONLY_SUFFIX = '-raw-only'

export function isRawOnly(meta: Pick<Metadata, 'method_version'> | null | undefined): boolean {
  return meta?.method_version.endsWith(RAW_ONLY_SUFFIX) === true
}

/** A record of the raw-only products: its method version ends in `-raw-only` or it says NOT_HARMONIZED. */
export function isRawOnlyRecord(record: { method_version: string; reason_codes: readonly ReasonCode[] }): boolean {
  return record.method_version.endsWith(RAW_ONLY_SUFFIX) || record.reason_codes.includes('NOT_HARMONIZED')
}

/**
 * Whether a series is raw-only, decided from the series itself (the global metadata only says
 * what the map products are). `undefined` or an empty series falls back to the global value.
 */
export function isRawOnlySeries(
  records: readonly { method_version: string; reason_codes: readonly ReasonCode[] }[] | undefined,
  globalRawOnly: boolean,
): boolean {
  if (!globalRawOnly) return false
  if (records === undefined || records.length === 0) return globalRawOnly
  return records.every(isRawOnlyRecord)
}

/** Shown near the top while the products are raw-only (wording from the Lead's T-039 answer). */
export const RAW_ONLY_NOTE =
  'Raw data only, harmonization in progress. Estimates, intervals, baselines, % of normal, probabilities and verdicts are not available yet.'

/** In a view that needs a harmonized value or an area series that does not exist yet. */
export const NOT_AVAILABLE_YET = 'Not available yet: raw data only, harmonization in progress.'

export const RAW_ONLY_AREA_UNAVAILABLE =
  'Not available yet: totals for a country, continent or the world are not part of the raw-only data. The map and its cells are.'

export const RAW_ONLY_HARMONIZED_UNAVAILABLE =
  'Harmonized values and verdicts are not available yet (raw data only).'

/** True while the products are raw-only; the views that need harmonized data say so. */
export const RawOnlyContext = createContext(false)

export function useRawOnly(): boolean {
  return useContext(RawOnlyContext)
}
