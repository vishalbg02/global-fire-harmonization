import { describe, expect, it } from 'vitest'
import { DEFAULT_SAT_DAY } from '../components/map/gibs.ts'
import { SHOW_ALL_PARAM, applyMapViewParams, mapViewFromSearch, mapViewReducer } from './mapView.ts'
import type { MapViewAction, MapViewState } from './mapView.ts'

const base: MapViewState = { shape: 'flat', satOn: false, satDay: DEFAULT_SAT_DAY, showAll: false }

describe('the map view a link describes (T-093)', () => {
  it('opens a bare address (a first visit at the world view) on the globe', () => {
    expect(mapViewFromSearch('')).toEqual({ ...base, shape: 'globe' })
    expect(mapViewFromSearch('?')).toEqual({ ...base, shape: 'globe' })
  })

  it('opens globe=1 on the globe and globe=0 flat, whatever else the link carries', () => {
    expect(mapViewFromSearch('?globe=1').shape).toBe('globe')
    expect(mapViewFromSearch('?area=COUNTRY:IDN&month=2015-09&globe=1').shape).toBe('globe')
    expect(mapViewFromSearch('?globe=0').shape).toBe('flat')
    expect(mapViewFromSearch('?month=2015-09&globe=0').shape).toBe('flat')
  })

  it('keeps the flat map of an older link that has other parameters and no globe', () => {
    expect(mapViewFromSearch('?month=2015-09').shape).toBe('flat')
    expect(mapViewFromSearch('?area=COUNTRY:CAN&month=2023-08&sat=1').shape).toBe('flat')
    expect(mapViewFromSearch('?globe=yes').shape).toBe('flat')
  })

  it('reads Satellite view, its day and "show all verdicts"', () => {
    expect(mapViewFromSearch('?month=2015-09&sat=1&satday=20')).toEqual({ ...base, satOn: true, satDay: 20 })
    expect(mapViewFromSearch(`?month=2015-09&${SHOW_ALL_PARAM}=1`).showAll).toBe(true)
    expect(mapViewFromSearch('?month=2015-09&sat=0').satOn).toBe(false)
    expect(mapViewFromSearch(`?month=2015-09&${SHOW_ALL_PARAM}=0`).showAll).toBe(false)
  })

  it('falls back to the default day for a day outside 1 to 31 or not a whole number', () => {
    for (const bad of ['0', '32', '99', '-3', '7.5', 'x', '']) {
      expect(mapViewFromSearch(`?sat=1&satday=${bad}`).satDay).toBe(DEFAULT_SAT_DAY)
    }
    expect(mapViewFromSearch('?sat=1&satday=1').satDay).toBe(1)
    expect(mapViewFromSearch('?sat=1&satday=31').satDay).toBe(31)
  })
})

describe('the map view written into a link', () => {
  it('always writes the shape, and leaves the other defaults out', () => {
    const flat = new URLSearchParams()
    applyMapViewParams(flat, base)
    expect(flat.toString()).toBe('globe=0')
    const globe = new URLSearchParams()
    applyMapViewParams(globe, { ...base, shape: 'globe' })
    expect(globe.toString()).toBe('globe=1')
  })

  it('writes Satellite view, a day other than the default, and "show all verdicts"; keeps the other parameters', () => {
    const p = new URLSearchParams('area=COUNTRY%3AIDN&month=2015-09')
    applyMapViewParams(p, { shape: 'globe', satOn: true, satDay: 20, showAll: true })
    expect(p.toString()).toBe(`area=COUNTRY%3AIDN&month=2015-09&sat=1&satday=20&globe=1&${SHOW_ALL_PARAM}=1`)
    applyMapViewParams(p, { shape: 'flat', satOn: false, satDay: 20, showAll: false })
    expect(p.toString()).toBe('area=COUNTRY%3AIDN&month=2015-09&globe=0')
    applyMapViewParams(p, { shape: 'flat', satOn: true, satDay: DEFAULT_SAT_DAY, showAll: false })
    expect(p.toString()).toBe('area=COUNTRY%3AIDN&month=2015-09&sat=1&globe=0')
  })

  it('replaces earlier view parameters instead of adding a second copy', () => {
    const p = new URLSearchParams(`globe=1&sat=1&satday=3&${SHOW_ALL_PARAM}=1&month=2015-09`)
    applyMapViewParams(p, base)
    expect(p.getAll('globe')).toEqual(['0'])
    expect(p.has('sat')).toBe(false)
    expect(p.has('satday')).toBe(false)
    expect(p.has(SHOW_ALL_PARAM)).toBe(false)
  })

  it('reads back every view exactly, with or without other parameters (round trip)', () => {
    for (const shape of ['flat', 'globe'] as const) {
      for (const satOn of [false, true]) {
        for (const satDay of [1, DEFAULT_SAT_DAY, 28, 31]) {
          for (const showAll of [false, true]) {
            for (const others of ['', 'area=COUNTRY%3AIDN&month=2015-09']) {
              const view: MapViewState = { shape, satOn, satDay, showAll }
              const p = new URLSearchParams(others)
              applyMapViewParams(p, view)
              // The day is kept in the link only with Satellite view on; off, it comes back as the default.
              expect(mapViewFromSearch(`?${p.toString()}`)).toEqual({ ...view, satDay: satOn ? satDay : DEFAULT_SAT_DAY })
            }
          }
        }
      }
    }
  })
})

describe('map view changes', () => {
  const run = (state: MapViewState, ...actions: MapViewAction[]) => actions.reduce(mapViewReducer, state)

  it('sets and toggles the shape', () => {
    expect(run(base, { type: 'set-shape', shape: 'globe' }).shape).toBe('globe')
    expect(run(base, { type: 'toggle-shape' }).shape).toBe('globe')
    expect(run(base, { type: 'toggle-shape' }, { type: 'toggle-shape' }).shape).toBe('flat')
  })

  it('returns the same object when nothing changes, so the link and the map are not touched', () => {
    expect(mapViewReducer(base, { type: 'set-shape', shape: 'flat' })).toBe(base)
    expect(mapViewReducer(base, { type: 'set-sat', on: false })).toBe(base)
    expect(mapViewReducer(base, { type: 'set-show-all', on: false })).toBe(base)
    expect(mapViewReducer(base, { type: 'set-sat-day', day: 0 })).toBe(base)
  })

  it('sets and toggles Satellite view', () => {
    expect(run(base, { type: 'set-sat', on: true }).satOn).toBe(true)
    expect(run(base, { type: 'toggle-sat' }).satOn).toBe(true)
    expect(run(base, { type: 'toggle-sat' }, { type: 'toggle-sat' }).satOn).toBe(false)
  })

  it('takes a day from 1 to 31 and ignores any other', () => {
    expect(run(base, { type: 'set-sat-day', day: 1 }).satDay).toBe(1)
    expect(run(base, { type: 'set-sat-day', day: 31 }).satDay).toBe(31)
    for (const day of [0, 32, 2.5, Number.NaN, -1]) expect(run(base, { type: 'set-sat-day', day }).satDay).toBe(DEFAULT_SAT_DAY)
  })

  it('sets "show all verdicts" and leaves the other choices alone', () => {
    const start: MapViewState = { shape: 'globe', satOn: true, satDay: 9, showAll: false }
    expect(run(start, { type: 'set-show-all', on: true })).toEqual({ ...start, showAll: true })
    expect(run(start, { type: 'set-show-all', on: true }, { type: 'set-show-all', on: false })).toEqual(start)
  })

  it('a fallback to flat (the globe cannot render) is an ordinary shape change', () => {
    const globe: MapViewState = { ...base, shape: 'globe', showAll: true }
    expect(run(globe, { type: 'set-shape', shape: 'flat' })).toEqual({ ...globe, shape: 'flat' })
  })
})
