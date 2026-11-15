import { renderToString } from 'react-dom/server'
import { describe, expect, it } from 'vitest'
import { BAR_INTERVAL_MISSING, BAR_NONE, BAR_NOT_AVAILABLE, BAR_TEXT } from '../../content/answer.ts'
import { SPARK_UNIT } from '../../content/ui.ts'
import { NO_DATA, formatPctOfNormal, oneDecimal } from '../map/format.ts'
import { IntervalBar } from './IntervalBar.tsx'
import { MIN_SPAN, intervalBar, intervalValues } from './intervalBar.ts'
import type { IntervalValues } from './intervalBar.ts'
import { intervalTexts, pctParts } from './text.ts'

// SYNTHETIC test data, not NASA observations: round numbers whose positions are easy to check by hand.
const W = 320
const PAD = 10
const NONE: IntervalValues = { estimate: null, low: null, high: null, p25: null, p75: null, median: null }
const v = (over: Partial<IntervalValues>): IntervalValues => ({ ...NONE, ...over })
// With pad 10 on a 320 line, 300 units of width are left: 1 value unit is 1.5 drawing units when the domain is 0..200.
const x = (value: number, top = 200) => PAD + (value / top) * (W - 2 * PAD)

describe('interval bar geometry', () => {
  it('places the estimate, the interval, the normal range and the median on one line from 0', () => {
    const g = intervalBar(v({ estimate: 150, low: 120, high: 200, p25: 40, p75: 80, median: 60 }), W, PAD)!
    expect(g.domain).toEqual([0, 200])
    expect(g.origin).toBe(PAD)
    expect(g.estimate).toBe(x(150))
    expect(g.interval).toEqual({ x: x(120), w: x(200) - x(120) })
    expect(g.band).toEqual({ x: x(40), w: x(80) - x(40) })
    expect(g.median).toBe(x(60))
    // "Above normal" is visible: the whole interval is to the right of the band.
    expect(g.interval!.x).toBeGreaterThan(g.band!.x + g.band!.w)
  })

  it('never draws past the line: the largest value sits at the right end, inside the padding', () => {
    const g = intervalBar(v({ estimate: 50, low: 40, high: 60, p25: 30, p75: 70 }), W, PAD)!
    const right = g.band!.x + g.band!.w
    expect(right).toBe(W - PAD)
    expect(g.estimate).toBeGreaterThanOrEqual(PAD)
  })

  it('copes with a very high month (the band stays visible at the minimum width)', () => {
    // About 1000% of normal: a band of 0.5 to 3.5 against an estimate of 13,600.
    const g = intervalBar(v({ estimate: 13600, low: 12300, high: 15000, p25: 0.5, p75: 3.5, median: 1.3 }), W, PAD)!
    expect(g.domain).toEqual([0, 15000])
    expect(g.band!.w).toBeGreaterThanOrEqual(MIN_SPAN)
    expect(g.band!.x).toBeGreaterThanOrEqual(0)
    expect(g.estimate).toBeGreaterThan(W * 0.8)
    expect(g.interval!.x + g.interval!.w).toBeLessThanOrEqual(W)
  })

  it('a very narrow interval is drawn at the minimum width, centred on its value', () => {
    const g = intervalBar(v({ estimate: 100, low: 100, high: 100.001 }), W, PAD)!
    expect(g.interval!.w).toBe(MIN_SPAN)
    expect(Math.abs(g.interval!.x + MIN_SPAN / 2 - g.estimate!)).toBeLessThan(0.02)
  })

  it('draws an estimate outside its interval where it is (no value is moved)', () => {
    const g = intervalBar(v({ estimate: 190, low: 100, high: 150, p25: 20, p75: 60 }), W, PAD)!
    expect(g.domain).toEqual([0, 190])
    expect(g.estimate!).toBeGreaterThan(g.interval!.x + g.interval!.w)
  })

  it('takes the bounds in either order', () => {
    const a = intervalBar(v({ low: 100, high: 50, p25: 80, p75: 20 }), W, PAD)!
    const b = intervalBar(v({ low: 50, high: 100, p25: 20, p75: 80 }), W, PAD)!
    expect(a).toEqual(b)
  })

  it('starts below 0 only when a value is below 0', () => {
    const g = intervalBar(v({ estimate: 10, low: -10, high: 30 }), W, PAD)!
    expect(g.domain).toEqual([-10, 30])
    expect(g.origin).toBeGreaterThan(PAD)
    expect(g.interval!.x).toBe(PAD)
  })

  it('leaves out what is missing and never treats it as 0', () => {
    const noInterval = intervalBar(v({ estimate: 50, low: null, high: 70, p25: 10, p75: 30, median: 20 }), W, PAD)!
    expect(noInterval.interval).toBeNull()
    expect(noInterval.domain).toEqual([0, 50])
    const noBand = intervalBar(v({ estimate: 50, low: 40, high: 60, p25: 10, p75: null }), W, PAD)!
    expect(noBand.band).toBeNull()
    expect(noBand.median).toBeNull()
    const noEstimate = intervalBar(v({ p25: 10, p75: 30, median: 20 }), W, PAD)!
    expect(noEstimate.estimate).toBeNull()
    expect(noEstimate.interval).toBeNull()
    expect(noEstimate.band).not.toBeNull()
  })

  it('has nothing to draw when every value is missing (or not a finite number)', () => {
    expect(intervalBar(NONE, W)).toBeNull()
    expect(intervalBar(v({ estimate: Number.NaN, median: Number.POSITIVE_INFINITY }), W)).toBeNull()
  })

  it('a single value of 0 still has a domain to draw on', () => {
    const g = intervalBar(v({ estimate: 0 }), W, PAD)!
    expect(g.domain).toEqual([0, 1])
    expect(g.estimate).toBe(PAD)
  })

  it('reads the six stored fields by their contract names', () => {
    expect(
      intervalValues({ estimate: 1, ci90_low: 2, ci90_high: 3, baseline_p25: 4, baseline_p75: 5, baseline_median: 6 }),
    ).toEqual({ estimate: 1, low: 2, high: 3, p25: 4, p75: 5, median: 6 })
  })
})

describe('interval bar texts', () => {
  it('prints the stored values with one decimal, through oneDecimal', () => {
    const t = intervalTexts(v({ estimate: 19068.709, low: 17320.183, high: 20817.234, p25: 2190.706, p75: 10536.413, median: 7199.5 }))
    expect(t).toEqual({
      estimate: oneDecimal(19068.709),
      interval: `${oneDecimal(17320.183)} to ${oneDecimal(20817.234)}`,
      normal: `${oneDecimal(2190.706)} to ${oneDecimal(10536.413)}`,
      median: oneDecimal(7199.5),
    })
  })

  it('says what is missing in words, never 0', () => {
    expect(intervalTexts(NONE)).toEqual({ estimate: NO_DATA, interval: NO_DATA, normal: BAR_NOT_AVAILABLE, median: BAR_NOT_AVAILABLE })
    expect(intervalTexts(v({ estimate: 12, low: 10 })).interval).toBe(BAR_INTERVAL_MISSING)
    expect(intervalTexts(v({ estimate: 12, p25: 1 })).normal).toBe(BAR_NOT_AVAILABLE)
  })

  it('splits the big number from its unit exactly as formatPctOfNormal writes it', () => {
    expect(pctParts(264.86)).toEqual({ value: '265', unit: '% of normal' })
    expect(pctParts(1024.42)).toEqual({ value: '1024', unit: '% of normal' })
    expect(pctParts(0)).toEqual({ value: '0', unit: '% of normal' })
    expect(pctParts(null)).toBeNull()
    const parts = pctParts(91.44)!
    expect(`${parts.value}${parts.unit}`).toBe(formatPctOfNormal(91.44))
  })
})

describe('interval bar', () => {
  const record = { estimate: 150, ci90_low: 120, ci90_high: 200, baseline_p25: 40, baseline_p75: 80, baseline_median: 60 }

  it('is an image with a name and a sentence that reads the stored values, and a visible legend with the unit', () => {
    const html = renderToString(<IntervalBar record={record} areaName="Testland" />)
    expect(html).toContain('role="img"')
    expect(html).toContain('Testland: the estimate and its 90% interval against the normal range')
    expect(html).toContain(BAR_TEXT({ estimate: '150.0', interval: '120.0 to 200.0', normal: '40.0 to 80.0', median: '60.0', unit: SPARK_UNIT }))
    for (const text of ['150.0', '120.0 to 200.0', '40.0 to 80.0', '60.0', SPARK_UNIT]) expect(html).toContain(text)
  })

  it('tells the parts apart by shape: a hatched band, a solid bar, a dot and a dashed tick', () => {
    const html = renderToString(<IntervalBar record={record} areaName="Testland" />)
    expect(html).toMatch(/<pattern id="ibar-[^"]+-hatch"/)
    expect(html).toMatch(/fill="url\(#ibar-[^)]+-hatch\)"/)
    expect(html).toContain('class="ibar-interval"')
    expect(html).toContain('<circle')
    expect(html).toContain('class="ibar-median"')
  })

  it('has the explainers of the terms it uses', () => {
    const html = renderToString(<IntervalBar record={record} areaName="Testland" />)
    expect(html).toContain('What is 90% interval?')
    expect(html).toContain('What is normal range?')
    expect(html).toContain('What is Aqua-equivalent cell-days?')
  })

  it('draws nothing and says so when every value is missing; prints no computed number', () => {
    const html = renderToString(
      <IntervalBar record={{ estimate: null, ci90_low: null, ci90_high: null, baseline_p25: null, baseline_p75: null, baseline_median: null }} areaName="Testland" />,
    )
    expect(html).not.toContain('<svg viewBox="0 0 320')
    expect(html).toContain(BAR_NONE)
    expect(html).toContain(NO_DATA)
    expect(html).not.toMatch(/>\s*0(\.0)?\s*</)
  })
})
