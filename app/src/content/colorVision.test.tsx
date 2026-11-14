import { describe, expect, it } from 'vitest'
import { divergingRgb, NO_DATA_RGB, OUTSIDE_RGB, PCT_CENTRE, PCT_HIGH, PCT_LOW, sequentialRgb } from '../components/calendar/scales.ts'
import { renderToString } from 'react-dom/server'
import { CalendarLegend } from '../components/calendar/CalendarLegend.tsx'
import { Legend } from '../components/map/Legend.tsx'
import { buildHeatPoints } from '../components/calendar/chartOption.ts'
import { NO_DATA_COLOR, needsOutline } from '../components/map/scale.ts'
import {
  BASELINE_COLOR,
  HARMONIZED_COLOR,
  RAW_COMBINED_COLOR,
  WITNESS_STYLE,
} from '../components/witness/chartOption.ts'
import {
  contrastRatio,
  CVD_TYPES,
  deltaE2000,
  deltaE2000Rgb,
  parseColor,
  relativeLuminance,
  rgbToHex,
  rgbToLab,
  simulate,
  simulationFilterValues,
  type CvdType,
  type Lab,
  type Rgb,
} from './colorVision.ts'
import { VERDICT_PRESENTATION } from './verdicts.ts'

type Mode = 'normal' | CvdType
const MODES: readonly Mode[] = ['normal', ...CVD_TYPES]

/** Perceived colour of `rgb` under `mode`, as sRGB. */
function seen(rgb: Rgb, mode: Mode): Rgb {
  return mode === 'normal' ? rgb : simulate(rgb, mode)
}
function lightness(rgb: Rgb, mode: Mode): number {
  return rgbToLab(seen(rgb, mode))[0]
}
function deltaE(a: Rgb, b: Rgb, mode: Mode): number {
  return deltaE2000Rgb(a, b, mode === 'normal' ? undefined : mode)
}

// A threshold chosen for this project, not a standard. CIEDE2000 of about 2.3 is a "just
// noticeable difference" for side-by-side patches; 10 is a clear, easy difference for thin lines
// and small fills seen apart. Anything below it is listed in an exception list with the reason.
const MIN_DELTA_E = 10

interface Item {
  rgb: Rgb
  /** A non-colour cue that also tells the item apart (icon, dash pattern, width). */
  cue: string
}
interface Failure {
  key: string
  deltaE: number
}

/** Every pair, under every mode, whose CIEDE2000 is below `threshold`; plus the minimum seen. */
function pairwise(set: Record<string, Item>, threshold: number) {
  const names = Object.keys(set)
  const failures: Failure[] = []
  let min = Infinity
  for (const mode of MODES) {
    for (let i = 0; i < names.length; i++) {
      for (let j = i + 1; j < names.length; j++) {
        const de = deltaE(set[names[i]].rgb, set[names[j]].rgb, mode)
        if (de < threshold) failures.push({ key: `${names[i]}|${names[j]}|${mode}`, deltaE: de })
        else min = Math.min(min, de)
      }
    }
  }
  return { failures, minPassing: min }
}

/** Failing pairs must equal the documented exceptions exactly, and each needs a differing cue. */
function expectOnlyDocumented(set: Record<string, Item>, exceptions: readonly string[]) {
  const { failures, minPassing } = pairwise(set, MIN_DELTA_E)
  expect(failures.map((f) => f.key).sort()).toEqual([...exceptions].sort())
  for (const key of exceptions) {
    const [a, b] = key.split('|')
    expect(set[a].cue).not.toBe(set[b].cue)
  }
  expect(minPassing).toBeGreaterThanOrEqual(MIN_DELTA_E)
}

// ---------------------------------------------------------------------------------------------
// The app's colours. Exported constants are imported; the others are replicated with their source.

// Replicated from src/components/witness/chartOption.ts (not exported).
const OUTAGE_MARK = '#b00020'
const DRIFT_MARK = '#8e44ad'
const PROVISIONAL_MARK = '#8a6d00'
// Replicated from src/components/calendar/scales.ts (NEUTRAL, not exported): the 100% colour.
const PCT_NEUTRAL: Rgb = [247, 247, 247]
// Replicated from src/components/map/MapView.tsx (map layer paint, not exported).
const MAP_LAND = parseColor('#f7f7f2')
const OUTLINE_ABOVE = '#D55E00'
const OUTLINE_BELOW = '#0072B2'
const OUTLINE_SELECTED = '#0050c8'
// Replicated from src/components/calendar/chartOption.ts (not exported).
const CAL_SELECTED_BORDER = '#0050c8'
const CAL_PROVISIONAL_BORDER = '#000000'
const CAL_GRID_BORDER = '#c9ccd3'

const dashKey = (d: readonly number[] | undefined) => (d === undefined ? 'solid' : d.join(','))
const verdictRgb = (k: keyof typeof VERDICT_PRESENTATION): Rgb => VERDICT_PRESENTATION[k].color

/** Composite a colour with alpha over the map's land fill, as deck.gl draws cell fills. */
function overLand(c: readonly number[], alpha: number): Rgb {
  const a = alpha / 255
  return [0, 1, 2].map((i) => c[i] * a + MAP_LAND[i] * (1 - a)) as unknown as Rgb
}

const RAMP_T = Array.from({ length: 21 }, (_, i) => i / 20)
const RAMP_STOPS = [0, 0.25, 0.5, 0.75, 1]

// ---------------------------------------------------------------------------------------------

describe('helpers against known values', () => {
  it('contrast ratio and luminance', () => {
    expect(contrastRatio([0, 0, 0], [255, 255, 255])).toBeCloseTo(21, 10)
    expect(contrastRatio([255, 255, 255], [0, 0, 0])).toBeCloseTo(21, 10)
    expect(contrastRatio([120, 30, 200], [120, 30, 200])).toBe(1)
    expect(relativeLuminance([255, 255, 255])).toBeCloseTo(1, 10)
    expect(relativeLuminance([0, 0, 0])).toBe(0)
    // #777777 on white is the textbook 4.48:1 (just under the 4.5 AA line).
    expect(contrastRatio([119, 119, 119], [255, 255, 255])).toBeCloseTo(4.48, 2)
  })

  it('parses hex and rgb() strings and round-trips hex', () => {
    expect(parseColor('#0050c8')).toEqual([0, 80, 200])
    expect(parseColor('#FA0')).toEqual([255, 170, 0])
    expect(parseColor('rgb(213, 94, 0)')).toEqual([213, 94, 0])
    expect(parseColor('rgba(1, 2, 3, 0.5)')).toEqual([1, 2, 3])
    expect(rgbToHex([213, 94, 0])).toBe('#d55e00')
    expect(() => parseColor('blue')).toThrow()
    expect(() => parseColor('rgb(300, 0, 0)')).toThrow()
  })

  it('Lab of white, black and sRGB red', () => {
    const w = rgbToLab([255, 255, 255])
    expect(w[0]).toBeCloseTo(100, 2)
    expect(Math.abs(w[1])).toBeLessThan(0.01)
    expect(Math.abs(w[2])).toBeLessThan(0.01)
    expect(rgbToLab([0, 0, 0])).toEqual([0, 0, 0])
    const red = rgbToLab([255, 0, 0])
    expect(red[0]).toBeCloseTo(53.24, 1)
    expect(red[1]).toBeCloseTo(80.09, 1)
    expect(red[2]).toBeCloseTo(67.2, 1)
  })

  // Sharma, Wu and Dalal (2005), "The CIEDE2000 colour-difference formula", test data.
  // Only the pairs whose values are certain are used.
  const SHARMA: [Lab, Lab, number][] = [
    [[50, 2.6772, -79.7751], [50, 0, -82.7485], 2.0425],
    [[50, 0, 0], [50, -1, 2], 2.3669],
    [[50, -1, 2], [50, 0, 0], 2.3669],
    [[50, 2.5, 0], [50, 0, -2.5], 4.3065],
    [[50, 2.5, 0], [73, 25, -18], 27.1492],
    [[50, 2.5, 0], [61, -5, 29], 22.8977],
    [[50, 2.5, 0], [56, -27, -3], 31.903],
    [[50, 2.5, 0], [58, 24, 15], 19.4535],
    [[60.2574, -34.0099, 36.2677], [60.4626, -34.1751, 39.4387], 1.2644],
    [[6.7747, -0.2908, -2.4247], [5.8714, -0.0985, -2.2286], 0.6377],
    [[2.0776, 0.0795, -1.135], [0.9033, -0.0636, -0.5514], 0.9082],
  ]
  it.each(SHARMA)('CIEDE2000 matches Sharma et al. 2005: %j vs %j', (a, b, expected) => {
    expect(deltaE2000(a, b)).toBeCloseTo(expected, 3)
    expect(deltaE2000(b, a)).toBeCloseTo(expected, 3)
  })

  it('CIEDE2000 of identical colours is 0', () => {
    expect(deltaE2000Rgb([10, 200, 30], [10, 200, 30])).toBe(0)
    expect(deltaE2000Rgb([10, 200, 30], [10, 200, 30], 'deuteranopia')).toBe(0)
  })

  it('greys stay grey under every simulation', () => {
    for (const type of CVD_TYPES) {
      for (const g of [0, 17, 64, 128, 153, 204, 242, 255]) {
        const out = simulate([g, g, g], type)
        for (const c of out) expect(Math.abs(c - g)).toBeLessThan(1) // matrix rows sum to 1 within 1e-5
        const lab = rgbToLab(out)
        expect(Math.hypot(lab[1], lab[2])).toBeLessThan(0.6)
      }
    }
  })

  it('simulation is clamped and keeps the primaries inside the gamut', () => {
    for (const type of CVD_TYPES) {
      for (const c of [[255, 0, 0], [0, 255, 0], [0, 0, 255], [255, 255, 0]] as Rgb[]) {
        for (const v of simulate(c, type)) {
          expect(v).toBeGreaterThanOrEqual(0)
          expect(v).toBeLessThanOrEqual(255)
        }
      }
    }
  })

  it('red and green collapse for protanopia and deuteranopia but not for tritanopia', () => {
    const red: Rgb = [255, 0, 0]
    const green: Rgb = [0, 160, 0]
    expect(deltaE2000Rgb(red, green)).toBeGreaterThan(40)
    expect(deltaE2000Rgb(red, green, 'tritanopia')).toBeGreaterThan(40)
    expect(deltaE2000Rgb(red, green, 'protanopia')).toBeLessThan(30)
    expect(deltaE2000Rgb(red, green, 'deuteranopia')).toBeLessThan(30)
  })

  it('feColorMatrix values are a 4x5 matrix with an untouched alpha row', () => {
    for (const type of CVD_TYPES) {
      const v = simulationFilterValues(type).split(' ').map(Number)
      expect(v).toHaveLength(20)
      expect(v.every(Number.isFinite)).toBe(true)
      expect(v.slice(15)).toEqual([0, 0, 0, 1, 0])
      for (const row of [0, 5, 10]) {
        expect(v.slice(row + 3, row + 5)).toEqual([0, 0])
        expect(v[row] + v[row + 1] + v[row + 2]).toBeCloseTo(1, 4)
      }
    }
    expect(simulationFilterValues('protanopia').startsWith('0.152286 1.052583 -0.204868 0 0')).toBe(true)
  })
})

describe('sequential ramps: L* increases with value', () => {
  // The map activity ramp (viridis stops in src/components/map/scale.ts) is also the calendar
  // activity ramp: scales.ts sequentialRgb calls it. One ramp, two uses.
  for (const [label, ts] of [['at its five stops', RAMP_STOPS], ['sampled at 21 points', RAMP_T]] as const) {
    for (const mode of MODES) {
      it(`activity ramp ${label}, ${mode}`, () => {
        const ls = ts.map((t) => lightness(sequentialRgb(t, 1), mode))
        for (let i = 1; i < ls.length; i++) expect(ls[i]).toBeGreaterThan(ls[i - 1])
      })
    }
  }

  it('has no exceptions: the ramp keeps its order under all three simulations', () => {
    for (const mode of MODES) {
      const ls = RAMP_STOPS.map((t) => lightness(sequentialRgb(t, 1), mode))
      expect(ls.every((l, i) => i === 0 || l > ls[i - 1])).toBe(true)
    }
  })
})

describe('categorical sets: pairwise CIEDE2000 under normal vision and each simulation', () => {
  it('verdict colours (src/content/verdicts.ts)', () => {
    const set: Record<string, Item> = {}
    for (const [k, p] of Object.entries(VERDICT_PRESENTATION)) set[k] = { rgb: p.color, cue: p.icon }
    // NO_DETECTED_ACTIVITY is a pale blue ([190, 215, 235]) so that it is seen on the land colour
    // without an outline (the first pale grey was 2.3 from the land). One pair stays just below
    // the threshold: that blue against the light grey of CANNOT_DETERMINE under protanopia (about
    // 8.9). They differ by icon (? against the open circle) and label.
    expectOnlyDocumented(set, ['CANNOT_DETERMINE|NO_DETECTED_ACTIVITY|protanopia'])
  })

  it('every verdict has a non-empty icon and label, all different (colour is never the only cue)', () => {
    const entries = Object.values(VERDICT_PRESENTATION)
    expect(entries).toHaveLength(5)
    for (const p of entries) {
      expect(p.icon.trim()).not.toBe('')
      expect(p.label.trim()).not.toBe('')
    }
    expect(new Set(entries.map((p) => p.icon)).size).toBe(entries.length)
    expect(new Set(entries.map((p) => p.label)).size).toBe(entries.length)
  })

  it('witness line colours (src/components/witness/chartOption.ts)', () => {
    const set: Record<string, Item> = {}
    for (const [k, s] of Object.entries(WITNESS_STYLE)) set[k] = { rgb: parseColor(s.color), cue: dashKey(s.dash) }
    // No exceptions. Tightest pair: SNPP_VIIRS against NOAA20_VIIRS under tritanopia (10.9).
    expectOnlyDocumented(set, [])
  })

  it('witness dash patterns are pairwise different', () => {
    const dashes = Object.values(WITNESS_STYLE).map((s) => dashKey(s.dash))
    expect(new Set(dashes).size).toBe(dashes.length)
  })

  it('chart lines: harmonized, baseline, raw combined and the witnesses', () => {
    const set: Record<string, Item> = {
      HARMONIZED: { rgb: parseColor(HARMONIZED_COLOR), cue: 'solid 2' },
      BASELINE: { rgb: parseColor(BASELINE_COLOR), cue: 'dashed 1' },
      RAW_COMBINED: { rgb: parseColor(RAW_COMBINED_COLOR), cue: 'dashed 1.5' },
    }
    for (const [k, s] of Object.entries(WITNESS_STYLE)) set[k] = { rgb: parseColor(s.color), cue: dashKey(s.dash) }
    // The baseline and raw-combined greys were 8.1 apart (a real failure found by this check);
    // the raw-combined line is now near black, so there are no exceptions.
    expectOnlyDocumented(set, [])
  })

  it('month marks on the witness chart: outage, drift era, provisional (and the harmonized line)', () => {
    const set: Record<string, Item> = {
      HARMONIZED_LINE: { rgb: parseColor(HARMONIZED_COLOR), cue: 'line 2' },
      OUTAGE: { rgb: parseColor(OUTAGE_MARK), cue: 'solid tick' },
      DRIFT: { rgb: parseColor(DRIFT_MARK), cue: 'dashed tick' },
      PROVISIONAL: { rgb: parseColor(PROVISIONAL_MARK), cue: 'dotted tick' },
    }
    // Documented exceptions, real failures (marks are drawn at 0.6 opacity, which makes it
    // worse, not better; opacity is not modelled here). Each pair differs by line style.
    expectOnlyDocumented(set, [
      'HARMONIZED_LINE|DRIFT|protanopia', // about 3.0: blue line and purple tick look alike
      'HARMONIZED_LINE|DRIFT|deuteranopia', // about 8.0
      'OUTAGE|PROVISIONAL|deuteranopia', // about 7.6: dark red and olive-brown
    ])
  })

  it('outlines: anomaly above, anomaly below, selected (src/components/map/MapView.tsx)', () => {
    const set: Record<string, Item> = {
      ABOVE: { rgb: parseColor(OUTLINE_ABOVE), cue: 'solid 2' },
      BELOW: { rgb: parseColor(OUTLINE_BELOW), cue: 'dashed 2' },
      SELECTED: { rgb: parseColor(OUTLINE_SELECTED), cue: 'solid 2.5' },
    }
    // Documented exception, real failure: the below-normal blue #0072B2 and the selected-country
    // blue #0050c8 are 13.7 apart with normal vision (passes) but 7.7 to 8.8 under the simulations (fails).
    // They differ by dash (dashed against solid) and width (2 against 2.5), not by colour.
    expectOnlyDocumented(set, [
      'BELOW|SELECTED|protanopia',
      'BELOW|SELECTED|deuteranopia',
      'BELOW|SELECTED|tritanopia',
    ])
  })

  it('calendar cell borders: selected, provisional, grid (src/components/calendar/chartOption.ts)', () => {
    const set: Record<string, Item> = {
      SELECTED: { rgb: parseColor(CAL_SELECTED_BORDER), cue: 'solid 3' },
      PROVISIONAL: { rgb: parseColor(CAL_PROVISIONAL_BORDER), cue: 'dashed 2' },
      GRID: { rgb: parseColor(CAL_GRID_BORDER), cue: 'solid 1' },
    }
    expectOnlyDocumented(set, [])
  })
})

describe('diverging % of normal ramp', () => {
  const at = (p: number) => divergingRgb(p)

  it('is centred at 100 and clamped to 0 and 200', () => {
    expect([PCT_LOW, PCT_CENTRE, PCT_HIGH]).toEqual([0, 100, 200])
    expect(at(100)).toEqual(PCT_NEUTRAL)
    expect(at(-50)).toEqual(at(0))
    expect(at(450)).toEqual(at(200))
    expect(at(99.999)).not.toEqual(at(150))
  })

  for (const mode of MODES) {
    it(`lightness rises to the centre and falls away from it, ${mode}`, () => {
      const below = [0, 25, 50, 75, 100].map((p) => lightness(at(p), mode))
      const above = [100, 125, 150, 175, 200].map((p) => lightness(at(p), mode))
      for (let i = 1; i < below.length; i++) expect(below[i]).toBeGreaterThan(below[i - 1])
      for (let i = 1; i < above.length; i++) expect(above[i]).toBeLessThan(above[i - 1])
    })

    it(`below side, above side and the middle stay distinguishable, ${mode}`, () => {
      const belowStops = [0, 50]
      const aboveStops = [150, 200]
      for (const b of belowStops) {
        expect(deltaE(at(b), at(100), mode)).toBeGreaterThanOrEqual(MIN_DELTA_E)
        for (const a of aboveStops) expect(deltaE(at(b), at(a), mode)).toBeGreaterThanOrEqual(MIN_DELTA_E)
      }
      for (const a of aboveStops) expect(deltaE(at(a), at(100), mode)).toBeGreaterThanOrEqual(MIN_DELTA_E)
    })
  }
})

describe('neutral fills that must not be mistaken for data', () => {
  // Real failures, pinned as exceptions. Greys do not change under simulation, so the numbers
  // are the same for every vision type.
  it('calendar: no data, outside the record, and 100% of normal', () => {
    const set: Record<string, Item> = {
      NO_DATA: { rgb: NO_DATA_RGB, cue: 'no icon, grey' },
      OUTSIDE: { rgb: OUTSIDE_RGB, cue: 'diagonal cross in the chart, hatching in the table and legend' },
      PCT_100: { rgb: at100(), cue: 'verdict icon' },
    }
    const { failures } = pairwise(set, MIN_DELTA_E)
    const pairs = new Set(failures.map((f) => f.key.split('|').slice(0, 2).join('|')))
    // NO_DATA/OUTSIDE 6.5, NO_DATA/PCT_100 4.9, OUTSIDE/PCT_100 1.6 (all vision types).
    expect([...pairs].sort()).toEqual(['NO_DATA|OUTSIDE', 'NO_DATA|PCT_100', 'OUTSIDE|PCT_100'])
    expect(deltaE(OUTSIDE_RGB, PCT_NEUTRAL, 'normal')).toBeLessThan(2)
    // The colour does not separate OUTSIDE from the 100% colour, so the cue must exist (T-042):
    // the chart draws a diagonal cross on every outside cell and none on the others.
    const rows = [
      {
        year: 2002,
        cells: [
          { year: 2002, month: 1, kind: 'outside', record: null, provisional: false },
          { year: 2002, month: 8, kind: 'no-record', record: null, provisional: false },
        ],
      },
    ] as unknown as Parameters<typeof buildHeatPoints>[0]
    expect(buildHeatPoints(rows, 'activity', 1, null, 'raw').map((p) => p.outside)).toEqual([true, false])
  })

  it('map: low-contrast fills over the land colour (cell alpha 220 and 200)', () => {
    const over = (rgb: readonly number[], alpha: number) => deltaE(overLand(rgb, alpha), MAP_LAND, 'normal')
    // "No detected activity" (about 65% of the real cell-months) is clear of the land colour by its
    // pale blue alone, in every mode (13.2 normal; the tightest simulation is protanopia, 12.3).
    for (const mode of MODES) {
      expect(deltaE(overLand(VERDICT_PRESENTATION.NO_DETECTED_ACTIVITY.color, 220), MAP_LAND, mode)).toBeGreaterThanOrEqual(MIN_DELTA_E)
    }
    expect(over(NO_DATA_COLOR, NO_DATA_COLOR[3])).toBeLessThan(3) // about 2.7
    // These two are separated by a dark outline, not by colour (T-042): the cell layer draws it
    // for exactly these cells (the verdict, or a null value in the activity layers).
    const cell = (verdict: string, raw: number | null) =>
      ({ verdict, raw_combined_cell_days: raw, estimate: null }) as unknown as Parameters<typeof needsOutline>[0]
    // The verdict layer has no outline: the land would turn black at world zoom (65% of the real
    // cell-months have no detected activity).
    expect(needsOutline(cell('NO_DETECTED_ACTIVITY', 0), 'verdict')).toBe(false)
    expect(needsOutline(cell('CANNOT_DETERMINE', 0), 'verdict')).toBe(false)
    expect(needsOutline(cell('WITHIN_NORMAL', null), 'raw')).toBe(true)
    expect(needsOutline(cell('WITHIN_NORMAL', 0), 'raw')).toBe(false)
    expect(over(verdictRgb('CANNOT_DETERMINE'), 220)).toBeLessThan(MIN_DELTA_E) // about 8.4
    // The other verdicts and the ramp ends are well clear of the land colour in every mode.
    for (const mode of MODES) {
      for (const k of ['ABOVE_NORMAL', 'BELOW_NORMAL', 'WITHIN_NORMAL'] as const) {
        expect(deltaE(overLand(verdictRgb(k), 220), MAP_LAND, mode)).toBeGreaterThanOrEqual(MIN_DELTA_E)
      }
      for (const t of RAMP_STOPS) {
        const c = sequentialRgb(t, 1)
        expect(deltaE(overLand(c, 210), MAP_LAND, mode)).toBeGreaterThanOrEqual(MIN_DELTA_E)
      }
    }
  })
})

function at100(): Rgb {
  return divergingRgb(PCT_CENTRE)
}

describe('legends show the same non-colour cues as the map and the calendar (T-042)', () => {
  it('the map legend marks "no data" with the dark outline; "no detected activity" has its own tone', () => {
    expect(renderToString(<Legend layer="verdict" max={0} />)).not.toContain('swatch-marked')
    expect(renderToString(<Legend layer="raw" max={10} />)).toContain('No data (dark outline)')
  })

  it('the calendar legend hatches "outside the record"', () => {
    const html = renderToString(
      <CalendarLegend mode="activity" maxActivity={10} source="raw" />,
    )
    expect(html).toContain('swatch-outside')
  })
})
