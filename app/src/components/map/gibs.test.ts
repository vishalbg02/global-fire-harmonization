import { describe, expect, it } from 'vitest'
import {
  CELL_OPACITY_IMAGERY,
  CELL_OPACITY_PLAIN,
  basemapTileUrl,
  cellOpacity,
  clampSatDay,
  daysInMonth,
  imageryFailed,
  imageryNote,
  isoDate,
  satDate,
  satDayRange,
  trueColourTileUrl,
} from './gibs.ts'

const TODAY = '2026-11-15'

describe('GIBS tile URLs', () => {
  it('builds the Blue Marble pattern with the fixed date', () => {
    expect(basemapTileUrl()).toBe(
      'https://gibs.earthdata.nasa.gov/wmts/epsg3857/best/BlueMarble_ShadedRelief_Bathymetry/default/2004-08-01/GoogleMapsCompatible_Level8/{z}/{y}/{x}.jpeg',
    )
  })
  it('builds the Aqua true-colour pattern for a day', () => {
    expect(trueColourTileUrl('2015-09-15')).toBe(
      'https://gibs.earthdata.nasa.gov/wmts/epsg3857/best/MODIS_Aqua_CorrectedReflectance_TrueColor/default/2015-09-15/GoogleMapsCompatible_Level9/{z}/{y}/{x}.jpg',
    )
  })
})

describe('Satellite view day', () => {
  it('knows the days of a month, leap years included', () => {
    expect(daysInMonth(2015, 9)).toBe(30)
    expect(daysInMonth(2016, 2)).toBe(29)
    expect(daysInMonth(2015, 2)).toBe(28)
  })
  it('defaults to the 15th and clamps to the days that exist', () => {
    expect(satDate(2015, 9, 15, TODAY)).toBe('2015-09-15')
    expect(satDate(2015, 2, 31, TODAY)).toBe('2015-02-28')
    expect(satDate(2015, 9, 0, TODAY)).toBe('2015-09-01')
    expect(clampSatDay(2015, 9, Number.NaN, TODAY)).toBe(15)
  })
  it('clamps the current month to today', () => {
    expect(satDate(2026, 11, 28, TODAY)).toBe('2026-11-15')
    expect(satDayRange(2026, 11, TODAY)).toEqual({ first: 1, last: 15 })
  })
  it('starts at the first Aqua day and is unavailable outside the range', () => {
    expect(satDayRange(2002, 7, TODAY)).toEqual({ first: 4, last: 31 })
    expect(satDate(2002, 7, 1, TODAY)).toBe('2002-07-04')
    expect(satDate(2002, 6, 15, TODAY)).toBeNull()
    expect(satDate(2027, 1, 15, TODAY)).toBeNull()
  })
  it('formats ISO dates with padding', () => {
    expect(isoDate(2015, 9, 5)).toBe('2015-09-05')
  })
})

describe('cell opacity and failure rule', () => {
  it('uses the Lead values', () => {
    expect(cellOpacity(true)).toBe(CELL_OPACITY_IMAGERY)
    expect(cellOpacity(false)).toBe(CELL_OPACITY_PLAIN)
    expect(CELL_OPACITY_IMAGERY).toBeLessThan(CELL_OPACITY_PLAIN)
  })
  it('treats a few missing tiles as normal and a blocked host as failure', () => {
    expect(imageryFailed({ ok: 10, failed: 2 })).toBe(false)
    expect(imageryFailed({ ok: 0, failed: 2 })).toBe(false)
    expect(imageryFailed({ ok: 1, failed: 5 })).toBe(true)
    expect(imageryFailed({ ok: 20, failed: 5 })).toBe(false)
  })
  it('shows the offline note, or one failure note, or nothing', () => {
    expect(imageryNote(true, false, false)).toBe('offline')
    expect(imageryNote(true, true, true)).toBe('offline')
    expect(imageryNote(false, true, true)).toBe('failed')
    expect(imageryNote(false, false, true)).toBe('failed')
    expect(imageryNote(false, false, false)).toBeNull()
  })
})
