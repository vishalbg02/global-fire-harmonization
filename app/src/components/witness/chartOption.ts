import type { EChartsCoreOption } from 'echarts/core'
import type { EntityMonth, Witness } from '../../api/contract.ts'
import { WITNESS_NAMES } from '../../content/witnesses.ts'
import {
  fieldSeries,
  monthLabels,
  monthsWithReason,
  provisionalMonths,
  rawCombinedSeries,
  witnessSeries,
  witnessesPresent,
} from './series.ts'

const HARMONIZED_COLOR = '#0050c8'
const BASELINE_COLOR = '#6b6b6b'
const RAW_COMBINED_COLOR = '#555555'
const BAND_ALPHA = 0.15

// Colour-blind-safe (Okabe-Ito) per witness, each paired with its own dash pattern so no two
// lines rely on colour alone to be told apart.
const WITNESS_STYLE: Record<Witness, { color: string; dash: number[] | undefined }> = {
  AQUA_MODIS: { color: '#D55E00', dash: [6, 3] },
  TERRA_MODIS: { color: '#009E73', dash: [2, 2] },
  SNPP_VIIRS: { color: '#CC79A7', dash: [1, 3] },
  NOAA20_VIIRS: { color: '#E69F00', dash: [8, 3, 2, 3] },
  NOAA21_VIIRS: { color: '#56B4E9', dash: [1, 1] },
}

/** A month in each list becomes one markLine tick of that colour; kept distinct per type. */
export interface MonthMarks {
  outage: string[]
  drift: string[]
  provisional: string[]
}

export function buildMonthMarks(records: readonly EntityMonth[]): MonthMarks {
  return {
    outage: monthsWithReason(records, 'OUTAGE'),
    drift: monthsWithReason(records, 'AQUA_DRIFT_ERA'),
    provisional: provisionalMonths(records),
  }
}

function markLine(months: readonly string[], color: string, lineType: 'solid' | 'dashed' | 'dotted') {
  return {
    symbol: 'none' as const,
    silent: true,
    lineStyle: { color, type: lineType, width: 1, opacity: 0.6 },
    label: { show: false },
    data: months.map((m) => ({ xAxis: m })),
  }
}

/** A band from `low` to `high`, drawn as a stacked invisible line plus a filled area on top. */
function band(low: (number | null)[], high: (number | null)[], color: string, name: string) {
  const diff = low.map((l, i) => {
    const h = high[i]
    return l === null || h === null ? null : h - l
  })
  const stack = `band-${name}`
  return [
    {
      name: `${name} (lower bound)`,
      type: 'line' as const,
      data: low,
      stack,
      symbol: 'none' as const,
      lineStyle: { opacity: 0 },
      areaStyle: { opacity: 0 },
      legendHoverLink: false,
      silent: true,
      tooltip: { show: false },
    },
    {
      name,
      type: 'line' as const,
      data: diff,
      stack,
      symbol: 'none' as const,
      lineStyle: { opacity: 0 },
      areaStyle: { color, opacity: BAND_ALPHA },
      tooltip: { show: false },
    },
  ]
}

/**
 * The time-series chart for one area's full history: the harmonized line and its 90% band, the
 * baseline band and median, the raw combined line, and one line per witness present in the
 * series. Outage, drift-era and provisional months are marked. No value here is computed:
 * every series is a stored field, read as given.
 */
export function buildWitnessChartOption(records: readonly EntityMonth[]): EChartsCoreOption {
  const categories = monthLabels(records)
  const marks = buildMonthMarks(records)
  const witnesses = witnessesPresent(records)

  const series: Record<string, unknown>[] = [
    ...band(fieldSeries(records, 'baseline_p25'), fieldSeries(records, 'baseline_p75'), BASELINE_COLOR, 'Baseline (25th-75th percentile)'),
    {
      name: 'Baseline (median)',
      type: 'line',
      data: fieldSeries(records, 'baseline_median'),
      symbol: 'none',
      lineStyle: { color: BASELINE_COLOR, type: 'dashed', width: 1 },
    },
    ...band(fieldSeries(records, 'ci90_low'), fieldSeries(records, 'ci90_high'), HARMONIZED_COLOR, 'Harmonized (90% interval)'),
    {
      name: 'Harmonized estimate',
      type: 'line',
      data: fieldSeries(records, 'estimate'),
      symbol: 'none',
      lineStyle: { color: HARMONIZED_COLOR, width: 2 },
      markLine: markLine(marks.outage, '#b00020', 'solid'),
    },
    {
      name: 'Raw combined (all satellites)',
      type: 'line',
      data: rawCombinedSeries(records),
      symbol: 'none',
      lineStyle: { color: RAW_COMBINED_COLOR, type: 'dashed', width: 1.5 },
      markLine: markLine(marks.drift, '#8e44ad', 'dashed'),
    },
    ...witnesses.map((w, i) => ({
      name: WITNESS_NAMES[w],
      type: 'line',
      data: witnessSeries(records, w),
      symbol: 'none',
      lineStyle: { color: WITNESS_STYLE[w].color, type: WITNESS_STYLE[w].dash ?? 'solid', width: 1.2 },
      markLine: i === witnesses.length - 1 ? markLine(marks.provisional, '#8a6d00', 'dotted') : undefined,
    })),
  ]

  return {
    animation: false,
    aria: {
      enabled: true,
      label: {
        description:
          'Time-series chart of satellite-detected fire activity: the harmonized estimate with its uncertainty band, the historical baseline band and median, the raw combined count, and one line per satellite. Outage months, Aqua-drift-era months and provisional months are marked. Use the table view for the values.',
      },
    },
    tooltip: { trigger: 'axis', confine: true },
    legend: { type: 'scroll', bottom: 0 },
    grid: { left: 56, right: 16, top: 24, bottom: 64 },
    xAxis: { type: 'category', data: categories, boundaryGap: false },
    yAxis: { type: 'value', name: 'fire-active cell-days' },
    dataZoom: [
      { type: 'inside', xAxisIndex: 0 },
      { type: 'slider', xAxisIndex: 0, bottom: 28, height: 18 },
    ],
    series,
  }
}
