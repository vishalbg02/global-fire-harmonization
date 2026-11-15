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
    // The world counts every cell; a country or a continent counts the cells stored for it (the cell list's country and continent).
    coverage: input.types[key][0] === 'GLOBAL' ? compute.coverage(input.cells.map((c) => ({ ...c, lat_min: 0, lat_max: 0, lon_min: 0, lon_max: 0 })), null)
      : compute.coverageInArea(input.cells, input.areas, input.types[key][0], input.types[key][1]),
  }
}
const [a, b] = input.compare
const compareRows = (rows) => rows.map((r) => ({ ...r }))
const out = { areas, compare: compute.compareSeries(compareRows(input.series[a]), compareRows(input.series[b])) }
process.stdout.write(JSON.stringify(out))
