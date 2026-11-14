import type { EChartsCoreOption } from 'echarts/core'
import { MONTH_ABBR } from '../../content/calendar.ts'
import type { ValueMode } from '../../state/selection.ts'
import type { CalendarRow } from './grid.ts'
import { cellVisual, NO_DATA_RGB, OUTSIDE_RGB, toCss } from './scales.ts'
import { cellLines, tooltipHtml } from './text.ts'

const SELECTED_BORDER = '#0050c8'
const PROVISIONAL_BORDER = '#000000'
const GRID_BORDER = '#c9ccd3'

/** The parts of ECharts' custom-series API that `renderItem` uses. */
interface CustomApi {
  value: (dimension: number) => number
  coord: (point: [number, number]) => [number, number]
  size: (point: [number, number]) => [number, number]
}

interface HeatPoint {
  value: [number, number, number]
  /** Index of the row and column in the grid, used by the tooltip and the click handler. */
  year: number
  month: number
  itemStyle: Record<string, unknown>
  label: Record<string, unknown>
}

/** One heatmap point per calendar cell, coloured and iconed by `cellVisual`. */
export function buildHeatPoints(
  rows: readonly CalendarRow[],
  mode: ValueMode,
  maxActivity: number,
  selected: { year: number; month: number } | null,
): HeatPoint[] {
  const points: HeatPoint[] = []
  rows.forEach((row, y) => {
    row.cells.forEach((cell, x) => {
      const isSelected = selected !== null && selected.year === cell.year && selected.month === cell.month
      let color = OUTSIDE_RGB
      let text = ''
      let textColor = '#000000'
      if (cell.kind === 'no-record') color = NO_DATA_RGB
      if (cell.kind === 'record' && cell.record !== null) {
        const visual = cellVisual(cell.record, mode, maxActivity)
        color = visual.color
        text = visual.icon
        textColor = toCss(visual.text)
      }
      points.push({
        value: [x, y, 0],
        year: cell.year,
        month: cell.month,
        itemStyle: {
          color: toCss(color),
          borderColor: isSelected ? SELECTED_BORDER : cell.provisional ? PROVISIONAL_BORDER : GRID_BORDER,
          borderWidth: isSelected ? 3 : cell.provisional ? 2 : 1,
          borderType: !isSelected && cell.provisional ? 'dashed' : 'solid',
        },
        label: { show: text !== '', formatter: text, color: textColor, fontSize: 12 },
      })
    })
  })
  return points
}

/** The ECharts option for the heatmap. Animation is off (reduced-motion friendly). */
export function buildChartOption(
  rows: readonly CalendarRow[],
  mode: ValueMode,
  maxActivity: number,
  selected: { year: number; month: number } | null,
  areaName: string,
): EChartsCoreOption {
  const cellByKey = new Map<string, CalendarRow['cells'][number]>()
  for (const row of rows) for (const cell of row.cells) cellByKey.set(`${cell.year}-${cell.month}`, cell)
  const points = buildHeatPoints(rows, mode, maxActivity, selected)
  const first = rows[0]?.year
  const last = rows[rows.length - 1]?.year
  return {
    animation: false,
    aria: {
      enabled: true,
      label: {
        description: `Calendar of satellite-detected fire activity for ${areaName}, one row per year from ${first} to ${last} and one column per month. Use the table view for the values.`,
      },
    },
    tooltip: {
      trigger: 'item',
      confine: true,
      formatter: (params: unknown) => {
        const data = (params as { data?: { year?: number; month?: number } }).data
        const cell = data?.year === undefined ? undefined : cellByKey.get(`${data.year}-${data.month}`)
        return cell === undefined ? '' : tooltipHtml(cell)
      },
    },
    grid: { left: 52, right: 8, top: 28, bottom: 8 },
    xAxis: {
      type: 'category',
      data: MONTH_ABBR,
      position: 'top',
      splitArea: { show: false },
      axisTick: { show: false },
    },
    yAxis: {
      type: 'category',
      data: rows.map((r) => String(r.year)),
      inverse: true,
      axisTick: { show: false },
    },
    series: [
      {
        // A custom series draws each cell's rectangle and icon exactly as styled by
        // `buildHeatPoints`. (ECharts' heatmap series needs a visualMap, which would override
        // the per-cell colours.)
        type: 'custom',
        data: points.map((p) => ({ value: p.value, year: p.year, month: p.month })),
        renderItem: (params: { dataIndex: number }, api: CustomApi) => {
          const point = points[params.dataIndex]
          const centre = api.coord([api.value(0), api.value(1)])
          const [width, height] = api.size([1, 1])
          const style = point.itemStyle
          const dashed = style.borderType === 'dashed'
          return {
            type: 'group',
            children: [
              {
                type: 'rect',
                shape: { x: centre[0] - width / 2, y: centre[1] - height / 2, width, height },
                style: {
                  fill: style.color,
                  stroke: style.borderColor,
                  lineWidth: style.borderWidth,
                  lineDash: dashed ? [4, 3] : undefined,
                },
              },
              {
                type: 'text',
                style: {
                  text: point.label.formatter,
                  x: centre[0],
                  y: centre[1],
                  fill: point.label.color,
                  font: '12px system-ui, sans-serif',
                  textAlign: 'center',
                  textVerticalAlign: 'middle',
                },
              },
            ],
          }
        },
      },
    ],
  }
}

/** Text of every cell, row by row (used to test that chart and table agree). */
export function chartCellTexts(rows: readonly CalendarRow[]): string[][] {
  return rows.map((row) => row.cells.map((cell) => cellLines(cell).join(' | ')))
}
