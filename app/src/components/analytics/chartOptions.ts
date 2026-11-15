import type { EChartsCoreOption } from 'echarts/core'
import { BASELINE_COLOR, HARMONIZED_COLOR, RAW_COMBINED_COLOR } from '../witness/chartOption.ts'
import { MONTH_NAMES, SATELLITE_JOINS } from './compute.ts'
import type { AnnualPoint, ComparePoint, SeasonPoint } from './compute.ts'

export const COMPARE_COLOR = '#D55E00'
const AXIS_TEXT = '#4a4a55'
const RULE = '#c9ccd3'

export const wholeNumber = (x: number) => Math.round(x).toLocaleString('en-US')

const axisBase = {
  axisLine: { lineStyle: { color: RULE } },
  axisLabel: { color: AXIS_TEXT },
  splitLine: { lineStyle: { color: RULE, opacity: 0.5, width: 1 } },
}

const grid = { left: 64, right: 16, top: 36, bottom: 36 }

/** 1. Annual sums of the harmonized estimate and of the raw combined count, with the satellite joins marked. A partial year is hollow. */
export function annualOption(points: readonly AnnualPoint[]): EChartsCoreOption {
  const years = points.map((p) => String(p.year))
  const hollow = (color: string, partial: boolean) => (partial ? { itemStyle: { color: '#ffffff', borderColor: color, borderWidth: 2 } } : {})
  const marks = SATELLITE_JOINS.filter((j) => years.includes(String(j.year))).map((j) => ({
    xAxis: String(j.year),
    label: { formatter: j.label, position: 'insideEndTop', color: AXIS_TEXT, fontSize: 11 },
    lineStyle: { color: AXIS_TEXT, type: 'dotted', width: 1 },
  }))
  return {
    animation: false,
    grid,
    legend: { top: 0, left: 0, textStyle: { color: AXIS_TEXT }, itemWidth: 18 },
    tooltip: {
      trigger: 'axis',
      valueFormatter: (v: unknown) => (typeof v === 'number' ? wholeNumber(v) : 'no data'),
    },
    xAxis: { type: 'category', data: years, ...axisBase },
    yAxis: { type: 'value', name: 'fire-active cell-days per year', nameTextStyle: { color: AXIS_TEXT, align: 'left' }, ...axisBase, axisLabel: { color: AXIS_TEXT, formatter: (v: number) => wholeNumber(v) } },
    series: [
      {
        name: 'Raw: all satellites combined, not converted',
        type: 'line',
        data: points.map((p) => ({ value: p.rawSum, ...hollow(RAW_COMBINED_COLOR, p.partial) })),
        symbolSize: 6,
        lineStyle: { color: RAW_COMBINED_COLOR, type: 'dashed', width: 1.5 },
        itemStyle: { color: RAW_COMBINED_COLOR },
        markLine: { symbol: 'none', silent: true, data: marks },
      },
      {
        name: 'Harmonized estimate (Aqua-equivalent)',
        type: 'line',
        data: points.map((p) => ({ value: p.harmonizedSum, ...hollow(HARMONIZED_COLOR, p.partial) })),
        symbolSize: 6,
        lineStyle: { color: HARMONIZED_COLOR, width: 2 },
        itemStyle: { color: HARMONIZED_COLOR },
      },
    ],
  }
}

/** 2. The normal band (p25 to p75) and median of each calendar month, with the selected year's line. */
export function seasonOption(points: readonly SeasonPoint[], year: number): EChartsCoreOption {
  const months = points.map((p) => MONTH_NAMES[p.month - 1].slice(0, 3))
  const low = points.map((p) => p.p25)
  const span = points.map((p) => (p.p25 === null || p.p75 === null ? null : p.p75 - p.p25))
  return {
    animation: false,
    grid,
    legend: { top: 0, left: 0, textStyle: { color: AXIS_TEXT }, itemWidth: 18 },
    tooltip: { trigger: 'axis', valueFormatter: (v: unknown) => (typeof v === 'number' ? wholeNumber(v) : 'no data') },
    xAxis: { type: 'category', data: months, ...axisBase },
    yAxis: { type: 'value', name: 'fire-active cell-days per month', nameTextStyle: { color: AXIS_TEXT, align: 'left' }, ...axisBase, axisLabel: { color: AXIS_TEXT, formatter: (v: number) => wholeNumber(v) } },
    series: [
      { name: 'Normal range base', type: 'line', stack: 'band', data: low, symbol: 'none', lineStyle: { opacity: 0 }, silent: true, tooltip: { show: false } },
      { name: 'Normal range (25th to 75th percentile, 2003 to 2022)', type: 'line', stack: 'band', data: span, symbol: 'none', lineStyle: { opacity: 0 }, areaStyle: { color: BASELINE_COLOR, opacity: 0.18 }, tooltip: { show: false } },
      { name: 'Normal median', type: 'line', data: points.map((p) => p.median), symbol: 'none', lineStyle: { color: BASELINE_COLOR, type: 'dashed', width: 1.2 } },
      { name: `${year}, harmonized estimate`, type: 'line', data: points.map((p) => p.selected), symbolSize: 6, lineStyle: { color: HARMONIZED_COLOR, width: 2 }, itemStyle: { color: HARMONIZED_COLOR } },
    ],
  }
}

/** 5. Two areas in % of normal, month by month, with the 100% line (a typical month). A missing month is a gap. */
export function compareOption(points: readonly ComparePoint[], nameA: string, nameB: string): EChartsCoreOption {
  return {
    animation: false,
    grid: { ...grid, bottom: 56 },
    legend: { top: 0, left: 0, textStyle: { color: AXIS_TEXT }, itemWidth: 18 },
    tooltip: { trigger: 'axis', valueFormatter: (v: unknown) => (typeof v === 'number' ? `${Math.round(v)}%` : 'no data') },
    dataZoom: [{ type: 'inside' }, { type: 'slider', height: 18, bottom: 8 }],
    xAxis: { type: 'category', data: points.map((p) => p.label), ...axisBase },
    yAxis: { type: 'value', name: '% of normal (100 = typical month)', nameTextStyle: { color: AXIS_TEXT, align: 'left' }, ...axisBase, axisLabel: { color: AXIS_TEXT, formatter: (v: number) => `${v}%` } },
    series: [
      { name: nameA, type: 'line', data: points.map((p) => p.a), symbol: 'none', connectNulls: false, lineStyle: { color: HARMONIZED_COLOR, width: 1.6 }, markLine: { symbol: 'none', silent: true, data: [{ yAxis: 100 }], lineStyle: { color: BASELINE_COLOR, type: 'dashed', width: 1 }, label: { formatter: '100%', color: AXIS_TEXT } } },
      { name: nameB, type: 'line', data: points.map((p) => p.b), symbol: 'none', connectNulls: false, lineStyle: { color: COMPARE_COLOR, width: 1.6, type: 'solid' } },
    ],
  }
}
