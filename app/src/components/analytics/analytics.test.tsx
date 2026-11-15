import { renderToString } from 'react-dom/server'
import { describe, expect, it } from 'vitest'
import { AnalyticsPanel } from './AnalyticsPanel.tsx'
import { annualOption, compareOption, seasonOption } from './chartOptions.ts'
import { chartSourceSegments, ANNUAL_NOTE, COVERAGE_NOTE } from './text.ts'
import { segmentsText } from '../../content/sources.ts'

// SYNTHETIC values: they exercise the structure of the options, not results.
const annual = [
  { year: 2011, monthsUsed: 12, harmonizedSum: 100, rawSum: 120, partial: false, provisional: false },
  { year: 2012, monthsUsed: 12, harmonizedSum: 105, rawSum: 400, partial: false, provisional: false },
  { year: 2026, monthsUsed: 10, harmonizedSum: 90, rawSum: 300, partial: true, provisional: true },
]

describe('analytics chart options', () => {
  it('marks the satellite joins that fall inside the record and shows a partial year as a hollow marker', () => {
    const o = annualOption(annual) as { series: { data: { value: number; itemStyle?: { color: string } }[]; markLine?: { data: { xAxis: string }[] } }[] }
    expect((annualOption(annual) as unknown as { title: { text: string } }).title.text).toContain('cell-days')
    expect(o.series[0].markLine?.data.map((d) => d.xAxis)).toEqual(['2012'])
    expect(o.series[1].data.map((d) => d.value)).toEqual([100, 105, 90])
    expect(o.series[1].data[2].itemStyle?.color).toBe('#ffffff')
    expect(o.series[1].data[0].itemStyle).toBeUndefined()
  })

  it('draws the season band as a base plus a span and keeps a missing month as null', () => {
    const o = seasonOption([{ month: 1, p25: 10, median: 20, p75: 30, selected: 15 }, { month: 2, p25: null, median: null, p75: null, selected: null }], 2020) as { series: { data: (number | null)[] }[] }
    expect(o.series[0].data).toEqual([10, null])
    expect(o.series[1].data).toEqual([20, null])
    expect(o.series[3].data).toEqual([15, null])
  })

  it('draws the comparison with a 100% line and gaps, never zeros', () => {
    const o = compareOption([{ label: '2020-01', a: 150, b: null }], 'A', 'B') as { series: { data: (number | null)[]; connectNulls: boolean }[] }
    expect(o.series[0].data).toEqual([150])
    expect(o.series[1].data).toEqual([null])
    expect(o.series[1].connectNulls).toBe(false)
  })
})

describe('analytics texts', () => {
  it('builds the source line from the metadata and the FIRMS link, with no typed dates', () => {
    const text = segmentsText(chartSourceSegments({ method_version: '0.1.0', first_month: '2002-07', latest_month: '2026-11', provisional_months: [] }))
    expect(text).toBe('Source: NASA FIRMS active-fire detections, harmonized by this project, method 0.1.0. Latest month 2026-11.')
    expect(chartSourceSegments({ method_version: '0.1.0', first_month: 'a', latest_month: 'b', provisional_months: [] })[1].href).toMatch(/^https:\/\/www\.earthdata\.nasa\.gov/)
  })
  it('states the limits the Lead asked for', () => {
    expect(ANNUAL_NOTE).toContain('Sum of monthly estimates; intervals not combined')
    expect(COVERAGE_NOTE).toContain('neighbouring areas')
    for (const t of [ANNUAL_NOTE, COVERAGE_NOTE]) expect(t).not.toContain('!')
  })
})

const text = (html: string) => html.replaceAll('<!-- -->', '')

describe('AnalyticsPanel', () => {
  it('renders its five sections as a self-contained component, loading its own data', () => {
    const html = text(renderToString(<AnalyticsPanel area={{ entityType: 'COUNTRY', entityId: 'IDN', name: 'Indonesia' }} compareArea={{ entityType: 'GLOBAL', entityId: 'GLOBAL', name: 'Global' }} year={2015} month={9} />))
    expect(html).toContain('Raw against harmonized, by year')
    expect(html).toContain('Season profile, 2015')
    expect(html).toContain('Rank in the record')
    expect(html).toContain('Coverage, September 2015')
    expect(html).toContain('Indonesia compared with Global')
    expect(html).toContain('Loading the series')
  })
  it('has no compare section without a second area', () => {
    const html = renderToString(<AnalyticsPanel area={{ entityType: 'GLOBAL', entityId: 'GLOBAL', name: 'Global' }} year={2020} month={1} />)
    expect(html).not.toContain('compared with')
  })
})
