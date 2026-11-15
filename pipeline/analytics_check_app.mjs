// Runs the analytics panel's own pure functions (app/src/components/analytics/compute.ts) on records read from the products.
// Node 22.6+ strips the TypeScript types. Used only by pipeline/analytics_check.py. Reads a JSON file, prints JSON.
import { readFileSync } from 'node:fs'
import { pathToFileURL } from 'node:url'
import { resolve } from 'node:path'

const compute = await import(pathToFileURL(resolve('app/src/components/analytics/compute.ts')).href)
const input = JSON.parse(readFileSync(process.argv[2], 'utf-8'))
const areas = {}
for (const [key, rows] of Object.entries(input.series)) {
  areas[key] = {
    annual: compute.annualSeries(rows),
    season: compute.seasonProfile(rows, input.year),
    rank: compute.rankInMonth(rows, input.year, input.month),
    coverage: compute.coverage(input.cells, input.boxes[key]),
  }
}
const [a, b] = input.compare
const compareRows = (rows) => rows.map((r) => ({ ...r }))
const out = { areas, compare: compute.compareSeries(compareRows(input.series[a]), compareRows(input.series[b])) }
process.stdout.write(JSON.stringify(out))
