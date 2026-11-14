import { useEffect, useRef } from 'react'
import { LineChart } from 'echarts/charts'
import {
  AriaComponent,
  DataZoomComponent,
  GridComponent,
  LegendComponent,
  MarkLineComponent,
  TooltipComponent,
} from 'echarts/components'
import * as echarts from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import type { EntityMonth } from '../../api/contract.ts'
import { buildWitnessChartOption } from './chartOption.ts'

echarts.use([
  LineChart,
  AriaComponent,
  DataZoomComponent,
  GridComponent,
  LegendComponent,
  MarkLineComponent,
  TooltipComponent,
  CanvasRenderer,
])

const CHART_HEIGHT = 360

/** The time-series chart. It is a canvas, so the table view is the keyboard route to the data. */
export function WitnessChart({ records, areaName }: { records: readonly EntityMonth[]; areaName: string }) {
  const container = useRef<HTMLDivElement>(null)
  const chartRef = useRef<echarts.ECharts | null>(null)

  useEffect(() => {
    if (container.current === null) return
    const chart = echarts.init(container.current)
    chartRef.current = chart
    const observer = new ResizeObserver(() => chart.resize())
    observer.observe(container.current)
    return () => {
      observer.disconnect()
      chart.dispose()
      chartRef.current = null
    }
  }, [])

  useEffect(() => {
    chartRef.current?.setOption(buildWitnessChartOption(records), true)
  }, [records])

  return (
    <div
      ref={container}
      className="witness-chart"
      style={{ height: CHART_HEIGHT }}
      role="img"
      aria-label={`Time-series chart of satellite-detected fire activity for ${areaName}. The table view gives the same values.`}
    />
  )
}
