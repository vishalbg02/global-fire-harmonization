import { useEffect, useRef } from 'react'
import { CustomChart } from 'echarts/charts'
import { AriaComponent, GridComponent, TooltipComponent } from 'echarts/components'
import * as echarts from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import type { ValueMode } from '../../state/selection.ts'
import { buildChartOption } from './chartOption.ts'
import type { CalendarRow } from './grid.ts'

echarts.use([CustomChart, AriaComponent, GridComponent, TooltipComponent, CanvasRenderer])

const ROW_HEIGHT = 22
const CHROME_HEIGHT = 40

interface Props {
  rows: readonly CalendarRow[]
  mode: ValueMode
  maxActivity: number
  selected: { year: number; month: number } | null
  areaName: string
  onSelectMonth: (year: number, month: number) => void
}

/** The ECharts heatmap. It is a canvas, so the table view is the keyboard route to the same data. */
export function CalendarChart({ rows, mode, maxActivity, selected, areaName, onSelectMonth }: Props) {
  const container = useRef<HTMLDivElement>(null)
  const chartRef = useRef<echarts.ECharts | null>(null)
  const onSelect = useRef(onSelectMonth)
  useEffect(() => {
    onSelect.current = onSelectMonth
  })

  useEffect(() => {
    if (container.current === null) return
    const chart = echarts.init(container.current)
    chartRef.current = chart
    chart.on('click', (params) => {
      const data = params.data as { year?: number; month?: number } | undefined
      if (data?.year !== undefined && data.month !== undefined) onSelect.current(data.year, data.month)
    })
    const observer = new ResizeObserver(() => chart.resize())
    observer.observe(container.current)
    return () => {
      observer.disconnect()
      chart.dispose()
      chartRef.current = null
    }
  }, [])

  useEffect(() => {
    chartRef.current?.setOption(buildChartOption(rows, mode, maxActivity, selected, areaName), true)
  }, [rows, mode, maxActivity, selected, areaName])

  return (
    <div
      ref={container}
      className="calendar-chart"
      style={{ height: rows.length * ROW_HEIGHT + CHROME_HEIGHT }}
      role="img"
      aria-label={`Calendar of satellite-detected fire activity for ${areaName}. The table view gives the same values.`}
    />
  )
}
