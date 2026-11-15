import { describe, expect, it } from 'vitest'
import { parseEntityMonth } from '../../api/contract.ts'
import type { EntityMonth } from '../../api/contract.ts'
import { SATELLITE_TIMELINE } from '../../content/witnessTimeline.ts'
import { monthKey, monthRange, offlineMapMonths } from '../../state/months.ts'
import {
  fractionOf,
  joinMarks,
  LABEL_GAP,
  LABEL_W,
  labelStep,
  lineSegments,
  monthAtFraction,
  monthIndex,
  playStep,
  provisionalSpans,
  rangeOf,
  sliderKeyTarget,
  snapToAvailable,
  unavailableSpans,
  yearTicks,
} from './timeline.ts'

// SYNTHETIC: a month list with the shape of the record (the real one comes from the metadata).
const ALL = monthRange('2002-07', '2026-11', ['2026-08', '2026-09', '2026-10', '2026-11'])
const R = rangeOf(ALL)!
const N = ALL.length - 1 // 292 month steps

describe('positions on the strip', () => {
  it('puts the first month at 0, the latest at 1 and the others evenly between', () => {
    expect(ALL.length).toBe(293)
    expect(fractionOf(R, { year: 2002, month: 7 })).toBe(0)
    expect(fractionOf(R, { year: 2026, month: 11 })).toBe(1)
    expect(fractionOf(R, { year: 2002, month: 8 })).toBeCloseTo(1 / N, 10)
    expect(fractionOf(R, { year: 2014, month: 9 })).toBeCloseTo(146 / N, 10)
  })

  it('clamps months outside the record to the ends', () => {
    expect(fractionOf(R, { year: 2001, month: 1 })).toBe(0)
    expect(fractionOf(R, { year: 2030, month: 1 })).toBe(1)
  })

  it('snaps a position to the nearest whole month, clamped to the record', () => {
    expect(monthAtFraction(R, 0)).toEqual({ year: 2002, month: 7 })
    expect(monthAtFraction(R, 1)).toEqual({ year: 2026, month: 11 })
    expect(monthAtFraction(R, 1.4)).toEqual({ year: 2026, month: 11 })
    expect(monthAtFraction(R, -0.2)).toEqual({ year: 2002, month: 7 })
    expect(monthAtFraction(R, 0.4 / N)).toEqual({ year: 2002, month: 7 })
    expect(monthAtFraction(R, 0.6 / N)).toEqual({ year: 2002, month: 8 })
    const m = { year: 2015, month: 9 }
    expect(monthAtFraction(R, fractionOf(R, m))).toEqual(m)
  })
})

describe('year ticks and labels for a width', () => {
  it('ticks every year of the record, the first at the first month', () => {
    const ticks = yearTicks(R, 1000)
    expect(ticks.map((t) => t.year)).toEqual(Array.from({ length: 25 }, (_, i) => 2002 + i))
    expect(ticks[0]!.f).toBe(0)
    expect(ticks[1]!.f).toBeCloseTo(fractionOf(R, { year: 2003, month: 1 }), 10)
  })

  it('labels every 2 years on a wide strip and every 4 on a phone, always with the first and latest year', () => {
    expect(labelStep(R, 1060)).toBe(2)
    expect(labelStep(R, 640)).toBe(2)
    expect(labelStep(R, 343)).toBe(4)
    expect(labelStep(R, 200)).toBe(8)
    const wide = yearTicks(R, 1060).filter((t) => t.labelled).map((t) => t.year)
    expect(wide).toEqual([2002, 2004, 2006, 2008, 2010, 2012, 2014, 2016, 2018, 2020, 2022, 2024, 2026])
    const phone = yearTicks(R, 400).filter((t) => t.labelled).map((t) => t.year)
    expect(phone).toEqual([2002, 2006, 2010, 2014, 2018, 2022, 2026])
    // At 343 px, 2006 would come within a few px of "2002" (the record starts in July 2002): it is dropped.
    expect(yearTicks(R, 343).filter((t) => t.labelled).map((t) => t.year)).toEqual([2002, 2010, 2014, 2018, 2022, 2026])
    const tiny = yearTicks(R, 200).filter((t) => t.labelled).map((t) => t.year)
    expect(tiny[0]).toBe(2002)
    expect(tiny[tiny.length - 1]).toBe(2026)
  })

  it('keeps labels apart, with the first and latest year always kept', () => {
    for (const r of [R, rangeOf(monthRange('2003-01', '2026-02', []))!, rangeOf(monthRange('2002-11', '2026-01', []))!]) {
      for (const width of [200, 343, 640, 1000]) {
        const labelled = yearTicks(r, width).filter((t) => t.labelled)
        // Centre to centre at least a label plus the gap (the end labels sit inside the strip, so this is the strictest case).
        for (let i = 1; i < labelled.length; i += 1) expect((labelled[i]!.f - labelled[i - 1]!.f) * width).toBeGreaterThanOrEqual(LABEL_W / 2 + LABEL_GAP)
        expect(labelled[0]!.f).toBe(0)
        expect(labelled[labelled.length - 1]!.year).toBe(2026)
      }
    }
  })

  it('anchors the end labels inside the strip', () => {
    const ticks = yearTicks(R, 343)
    expect(ticks[0]!.align).toBe('start')
    expect(ticks[ticks.length - 1]!.align).toBe('end')
    expect(ticks[12]!.align).toBe('middle')
  })
})

describe('provisional and unavailable spans', () => {
  it('shades the provisional months as one span covering whole months up to the end of the strip', () => {
    const spans = provisionalSpans(R, ['2026-08', '2026-09', '2026-10', '2026-11'])
    expect(spans).toHaveLength(1)
    expect(spans[0]!.from).toBeCloseTo((N - 3 - 0.5) / N, 10)
    expect(spans[0]!.to).toBe(1)
  })

  it('splits runs that are not consecutive, and ignores months outside the record', () => {
    const spans = provisionalSpans(R, ['2010-01', '2010-02', '2012-05', '1999-01'])
    expect(spans).toHaveLength(2)
    expect(spans[0]!.to - spans[0]!.from).toBeCloseTo(2 / N, 10)
    expect(spans[1]!.to - spans[1]!.from).toBeCloseTo(1 / N, 10)
    expect(provisionalSpans(R, [])).toEqual([])
  })

  it('dims the months that have no map in an offline copy, and nothing when every month has one', () => {
    const last24 = offlineMapMonths(ALL, ALL.slice(-24).map((m) => monthKey(m.year, m.month)))
    const spans = unavailableSpans(R, last24)
    expect(spans).toHaveLength(1)
    expect(spans[0]!.from).toBe(0)
    expect(spans[0]!.to).toBeCloseTo((N - 24 + 0.5) / N, 10)
    expect(unavailableSpans(R, ALL)).toEqual([])
  })
})

describe('satellite joins', () => {
  it('marks S-NPP VIIRS and NOAA-20 VIIRS at the months of content/witnessTimeline.ts', () => {
    const marks = joinMarks(R)
    expect(marks.map((m) => m.label)).toEqual(['S-NPP VIIRS', 'NOAA-20 VIIRS'])
    for (const m of marks) {
      const entry = SATELLITE_TIMELINE.find((e) => e.label === m.label)!
      expect(monthKey(m.month.year, m.month.month)).toBe(entry.start.slice(0, 7))
      expect(m.f).toBeCloseTo(fractionOf(R, m.month), 10)
    }
    expect(marks.map((m) => monthKey(m.month.year, m.month.month))).toEqual(['2012-01', '2018-04'])
    expect(marks.map((m) => m.short)).toEqual(['S-NPP', 'NOAA-20'])
  })

  it('leaves out a join outside the strip', () => {
    expect(joinMarks(rangeOf(monthRange('2002-07', '2011-12', []))!)).toEqual([])
  })
})

// SYNTHETIC series records: only the fields the line reads differ.
function rec(year: number, month: number, estimate: number | null, raw: number): EntityMonth {
  return parseEntityMonth({
    entity_type: 'GLOBAL', entity_id: 'GLOBAL', entity_name: 'World', year, month, n_cells: 1, raw_by_witness: null,
    estimate, ci90_low: null, ci90_high: null, sd: null, raw_combined_cell_days: raw, witnesses_used: ['AQUA_MODIS'],
    n_witnesses: 1, disagreement_scale: null, baseline_median: null, baseline_p25: null, baseline_p75: null,
    pct_of_normal: null, p_above: null, p_below: null, p_within: null, verdict: 'CANNOT_DETERMINE', reason_codes: [],
    data_level: 'SP', method_version: '0.1.0',
  })
}

describe('the background line', () => {
  const r = rangeOf(monthRange('2020-01', '2020-08', []))!
  const series = [rec(2020, 1, null, 5), rec(2020, 2, 10, 6), rec(2020, 3, 20, 7), rec(2020, 4, null, 8), rec(2020, 5, 0, 9), rec(2020, 6, 40, 10), rec(2020, 8, 30, 2)]

  it('leaves a gap at every null value and every month without a record, and never draws them at zero', () => {
    const segs = lineSegments(r, series, 'estimate')
    expect(segs.map((s) => s.length)).toEqual([2, 2, 1])
    const all = segs.flat()
    expect(all).toHaveLength(5)
    // February, March | May, June | August: January, April and July are not drawn.
    expect(segs[0]!.map((p) => Math.round(p.f * 7))).toEqual([1, 2])
    expect(segs[1]!.map((p) => Math.round(p.f * 7))).toEqual([4, 5])
    expect(segs[2]!.map((p) => Math.round(p.f * 7))).toEqual([7])
  })

  it('uses one linear scale from zero to the highest value; a real zero sits on the baseline', () => {
    const segs = lineSegments(r, series, 'estimate')
    expect(segs[0]!.map((p) => p.h)).toEqual([0.25, 0.5])
    expect(segs[1]!.map((p) => p.h)).toEqual([0, 1])
    expect(segs[2]![0]!.h).toBe(0.75)
  })

  it('draws the raw cell-days in the raw view (no nulls there, only missing records)', () => {
    const segs = lineSegments(r, series, 'raw_combined_cell_days')
    expect(segs.map((s) => s.length)).toEqual([6, 1])
    expect(segs[0]![5]!.h).toBe(1)
  })

  it('draws nothing while the series is loading or empty', () => {
    expect(lineSegments(r, undefined, 'estimate')).toEqual([])
    expect(lineSegments(r, [], 'estimate')).toEqual([])
    expect(lineSegments(r, [rec(2020, 1, null, 0)], 'estimate')).toEqual([])
  })
})

describe('snapping to the months that have a map', () => {
  const last24 = offlineMapMonths(ALL, ALL.slice(-24).map((m) => monthKey(m.year, m.month)))

  it('keeps an available month and moves any other to the nearest available one', () => {
    expect(snapToAvailable(ALL, { year: 2015, month: 9 })).toEqual({ year: 2015, month: 9, provisional: false })
    expect(snapToAvailable(last24, { year: 2010, month: 3 })).toMatchObject({ year: 2024, month: 12 })
    const gappy = ALL.filter((m) => m.year === 2010 && (m.month === 1 || m.month === 5))
    expect(snapToAvailable(gappy, { year: 2010, month: 2 })).toMatchObject({ month: 1 })
    expect(snapToAvailable(gappy, { year: 2010, month: 4 })).toMatchObject({ month: 5 })
    expect(snapToAvailable(gappy, { year: 2010, month: 3 })).toMatchObject({ month: 1 }) // a tie goes to the earlier month
    expect(snapToAvailable([], { year: 2010, month: 3 })).toBeNull()
  })
})

describe('slider keys', () => {
  const at = (year: number, month: number) => ({ year, month })
  const key = (k: string, from: { year: number; month: number } | null, list = ALL) => {
    const to = sliderKeyTarget(list, from, k)
    return to === null ? null : monthKey(to.year, to.month)
  }

  it('moves a month with the arrows (Up and Right forward), a year with Page Up and Page Down, and to the ends with Home and End', () => {
    expect(key('ArrowLeft', at(2015, 9))).toBe('2015-08')
    expect(key('ArrowDown', at(2015, 9))).toBe('2015-08')
    expect(key('ArrowRight', at(2015, 9))).toBe('2015-10')
    expect(key('ArrowUp', at(2015, 9))).toBe('2015-10')
    expect(key('PageUp', at(2015, 9))).toBe('2016-09')
    expect(key('PageDown', at(2015, 9))).toBe('2014-09')
    expect(key('Home', at(2015, 9))).toBe('2002-07')
    expect(key('End', at(2015, 9))).toBe('2026-11')
    expect(key('Enter', at(2015, 9))).toBeNull()
  })

  it('stops at the ends of the record, and a year step near an end goes to the end', () => {
    expect(key('ArrowLeft', at(2002, 7))).toBeNull()
    expect(key('ArrowRight', at(2026, 11))).toBeNull()
    expect(key('PageDown', at(2002, 12))).toBe('2002-07')
    expect(key('PageUp', at(2026, 3))).toBe('2026-11')
    expect(key('PageUp', at(2026, 11))).toBeNull()
  })

  it('reaches only months with a map, and steps from a month without one to the nearest on that side', () => {
    const last24 = offlineMapMonths(ALL, ALL.slice(-24).map((m) => monthKey(m.year, m.month)))
    expect(key('Home', at(2026, 1), last24)).toBe('2024-12')
    expect(key('ArrowRight', at(2010, 3), last24)).toBe('2024-12')
    expect(key('ArrowLeft', at(2010, 3), last24)).toBeNull()
    expect(key('PageDown', at(2025, 6), last24)).toBe('2024-12')
    expect(key('ArrowRight', null)).toBeNull()
    expect(key('Home', null, [])).toBeNull()
  })
})

describe('the time-lapse, with the play state owned outside', () => {
  const s = (o: Partial<Parameters<typeof playStep>[0]>) => playStep({ playing: true, justStarted: false, reduced: false, index: 5, count: 10, ...o })

  it('does nothing while paused', () => {
    expect(s({ playing: false })).toEqual({ type: 'idle' })
  })

  it('waits and shows the next month while playing, and stops after the latest month', () => {
    expect(s({})).toEqual({ type: 'wait', next: 6 })
    expect(s({ index: 9 })).toEqual({ type: 'stop' })
  })

  it('starts again from the first month when Play is pressed on the latest month or a month without a map', () => {
    expect(s({ justStarted: true, index: 9 })).toEqual({ type: 'go', index: 0 })
    expect(s({ justStarted: true, index: -1 })).toEqual({ type: 'go', index: 0 })
    expect(s({ justStarted: true, index: 3 })).toEqual({ type: 'wait', next: 4 })
  })

  it('switches the play state off at once under reduced motion or with no months (Space then does nothing)', () => {
    expect(s({ reduced: true })).toEqual({ type: 'stop' })
    expect(s({ reduced: true, justStarted: true })).toEqual({ type: 'stop' })
    expect(s({ count: 0, index: -1 })).toEqual({ type: 'stop' })
  })

  it('uses whole months only', () => {
    expect(monthIndex({ year: 2002, month: 7 }) + N).toBe(monthIndex({ year: 2026, month: 11 }))
  })
})
