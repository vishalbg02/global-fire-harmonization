import * as echarts from 'echarts/core'
import { SVGRenderer } from 'echarts/renderers'
import { afterEach, describe, expect, it, vi } from 'vitest'
// Importing the chart module registers the ECharts components the charts use.
import './AnalyticsChart.tsx'
import { annualOption, seasonOption } from './chartOptions.ts'

// SYNTHETIC points, only to build the options. Not NASA observations.
echarts.use([SVGRenderer])

afterEach(() => vi.restoreAllMocks())

describe('analytics charts register every ECharts component they use', () => {
  it('draws the annual and season options without an ECharts console error (for example "title is used but not imported")', () => {
    const errors: string[] = []
    vi.spyOn(console, 'error').mockImplementation((...a) => void errors.push(a.join(' ')))
    vi.spyOn(console, 'warn').mockImplementation((...a) => void errors.push(a.join(' ')))
    const annual = annualOption([
      { year: 2011, monthsUsed: 12, harmonizedSum: 100, rawSum: 90, partial: false, provisional: false },
      { year: 2012, monthsUsed: 12, harmonizedSum: 101, rawSum: 140, partial: false, provisional: false },
    ])
    const season = seasonOption([{ month: 1, p25: 1, median: 2, p75: 3, selected: 2 }], 2012)
    for (const option of [annual, season]) {
      const chart = echarts.init(null, null, { renderer: 'svg', ssr: true, width: 400, height: 260 })
      chart.setOption(option)
      chart.dispose()
    }
    expect(errors.filter((m) => /ECharts|not imported/i.test(m))).toEqual([])
  })
})
