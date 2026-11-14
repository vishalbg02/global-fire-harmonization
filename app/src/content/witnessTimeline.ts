import type { Witness } from '../api/contract.ts'

/**
 * Satellite record dates (fixed reference facts, not contract data), from
 * docs/DATA_SOURCES.md section 4, "Satellite record dates" [VERIFIED 2026-11-14, FIRMS FAQ],
 * with the Aqua/Terra 2026-11-14 checks [VERIFIED, T-008] and the S-NPP end date [VERIFIED].
 * Not computed; written here as text and dates, and never fetched from the API.
 */
export interface SatelliteTimelineEntry {
  witness: Witness
  label: string
  /** ISO date (and time, for the one entry that has one) the record starts. */
  start: string
  /** ISO date/time the record ends, or null if still ongoing. */
  end: string | null
  /** Shown next to the dates, e.g. "raw only" or "not used in the MVP". */
  note: string | null
}

export const SATELLITE_TIMELINE: SatelliteTimelineEntry[] = [
  {
    witness: 'TERRA_MODIS',
    label: 'Terra MODIS',
    start: '2000-11-01',
    end: null,
    note: 'raw view only; still delivering detections on 2026-11-14',
  },
  {
    witness: 'AQUA_MODIS',
    label: 'Aqua MODIS',
    start: '2002-07-01',
    end: null,
    note: 'still delivering detections on 2026-11-14; drifting late in life (AQUA_DRIFT_ERA)',
  },
  {
    witness: 'SNPP_VIIRS',
    label: 'S-NPP VIIRS',
    start: '2012-01-20',
    end: '2026-11-02T15:40:00Z',
    note: null,
  },
  {
    witness: 'NOAA20_VIIRS',
    label: 'NOAA-20 VIIRS',
    start: '2018-04-01',
    end: null,
    note: null,
  },
  {
    witness: 'NOAA21_VIIRS',
    label: 'NOAA-21 VIIRS',
    start: '2024-01-17',
    end: null,
    note: 'not used in the MVP',
  },
]

export const SATELLITE_TIMELINE_SOURCE =
  'docs/DATA_SOURCES.md, section 4, "Satellite record dates" [VERIFIED 2026-11-14, FIRMS FAQ]'
