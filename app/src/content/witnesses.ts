import type { Witness } from '../api/contract.ts'

export const WITNESS_NAMES: Record<Witness, string> = {
  AQUA_MODIS: 'Aqua MODIS',
  TERRA_MODIS: 'Terra MODIS (raw only)',
  SNPP_VIIRS: 'S-NPP VIIRS',
  NOAA20_VIIRS: 'NOAA-20 VIIRS',
  NOAA21_VIIRS: 'NOAA-21 VIIRS (reserved)',
}
