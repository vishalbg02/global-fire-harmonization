import type { EChartsCoreOption } from 'echarts/core'
import type { EntityMonth, Witness } from '../../api/contract.ts'
import { WITNESS_NAMES } from '../../content/witnesses.ts'
import { oneDecimal } from '../map/format.ts'
import {
  fieldSeries,
  monthLabels,
  monthsWithReason,
  provisionalMonths,
  rawCombinedSeries,
  witnessSeries,
  witnessesPresent,
} from './series.ts'

export const HARMONIZED_COLOR = '#0050c8'
export const BASELINE_COLOR = '#6b6b6b'
// Near black, so it stays apart from the grey baseline under every colour-vision type (T-042).
export const RAW_COMBINED_COLOR = '#1b1b1f'
const BAND_ALPHA = 0.15

// Colour-blind-safe (Okabe-Ito) per witness, each paired with its own dash pattern so no two
// lines rely on colour alone to be told apart.
export const WITNESS_STYLE: Record<Witness, { color: string; dash: number[] | undefined }> = {
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

/** The legend name of a satellite's own line: always marked as raw, as the other panels do. */
export function rawWitnessName(witness: Witness): string {
  return `Raw: ${WITNESS_NAMES[witness].replace(' (raw only)', '')}`
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

function hasValues(s: Record<string, unknown>): boolean {
  return (s.data as (number | null | undefined)[]).some((v) => v !== null && v !== undefined)
}

export const RAW_COMBINED_NAME = 'Raw: all satellites combined'
const LOWER_BOUND_SUFFIX = ' (lower bound)'

/** A band from `low` to `high`, drawn as a stacked invisible line plus a filled area on top. */
function band(low: (number | null)[], high: (number | null)[], color: string, name: string) {
  const diff = low.map((l, i) => {
    const h = high[i]
    return l === null || h === null ? null : h - l
  })
  const stack = `band-${name}`
  return [
    {
      name: `${name}${LOWER_BOUND_SUFFIX}`,
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
    ...band(fieldSeries(records, 'baseline_p25'), fieldSeries(records, 'baseline_p75'), BASELINE_COLOR, 'Baseline 25–75%'),
    {
      name: 'Baseline median',
      type: 'line',
      data: fieldSeries(records, 'baseline_median'),
      symbol: 'none',
      lineStyle: { color: BASELINE_COLOR, type: 'dashed', width: 1 },
    },
    ...band(fieldSeries(records, 'ci90_low'), fieldSeries(records, 'ci90_high'), HARMONIZED_COLOR, 'Harmonized 90% interval'),
    {
      name: 'Harmonized estimate',
      type: 'line',
      data: fieldSeries(records, 'estimate'),
      symbol: 'none',
      lineStyle: { color: HARMONIZED_COLOR, width: 2 },
      markLine: markLine(marks.outage, '#b00020', 'solid'),
    },
    {
      name: RAW_COMBINED_NAME,
      type: 'line',
      data: rawCombinedSeries(records),
      symbol: 'none',
      lineStyle: { color: RAW_COMBINED_COLOR, type: 'dashed', width: 1.5 },
      markLine: markLine(marks.drift, '#8e44ad', 'dashed'),
    },
    ...witnesses.map((w, i) => ({
      name: rawWitnessName(w),
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
    // One decimal, as in every other panel (the stored values are long floats).
    tooltip: {
      trigger: 'axis',
      confine: true,
      valueFormatter: (v: unknown) => (typeof v === 'number' ? oneDecimal(v) : String(v ?? '')),
    },
    // Only series that hold at least one stored value are listed (a missing product leaves none).
    // Every series is named in the legend, wrapped over rows (no paging); the helper entries of the
    // bands are left out.
    legend: {
      type: 'plain',
      top: 0,
      data: series
        .filter(hasValues)
        .map((s) => s.name as string)
        .filter((name) => !name.endsWith(LOWER_BOUND_SUFFIX)),
    },
    grid: { left: 64, right: 16, top: 84, bottom: 56 },
    xAxis: { type: 'category', data: categories, boundaryGap: false },
    yAxis: {
      type: 'value',
      name: 'fire-active cell-days',
      axisLabel: { formatter: (v: number) => (Number.isInteger(v) ? v.toLocaleString('en-US') : oneDecimal(v)) },
    },
    dataZoom: [
      { type: 'inside', xAxisIndex: 0 },
      { type: 'slider', xAxisIndex: 0, bottom: 8, height: 18 },
    ],
    series,
  }
}
