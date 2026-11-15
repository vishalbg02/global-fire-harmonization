// Calls the app's own formatting and counting helpers (TypeScript, imported through Node's type stripping) on values
// read from the products, for pipeline/number_check.py (T-026). Read-only use of app/: nothing is changed.
//
//   node pipeline/number_check_app.mjs input.json output.json
//
// input keys (all optional): probability [p], pct [v|null], estimate [{estimate, ci90_low, ci90_high}],
// verdictProbability [{verdict, p_above, p_below, p_within}], anomalyText [{entity_type, verdict, p_above, p_below, pct_of_normal}],
// ranking {anomalies: [...], tab, total}, statuses [tests], bboxLabel [[w, s, e, n]]
import { readFileSync, writeFileSync } from 'node:fs'

const [, , inputPath, outputPath] = process.argv
const base = new URL('../app/src/', import.meta.url)
const load = (file) => import(new URL(file, base).href)

const input = JSON.parse(readFileSync(inputPath, 'utf8'))
const out = {}

const fmt = await load('components/map/format.ts')
const rankings = await load('components/anomalies/rankings.ts')
const validation = await load('components/methods/validationFormat.ts')
const bbox = await load('state/bbox.ts')

if (input.probability) out.probability = input.probability.map((p) => fmt.formatProbability(p))
if (input.pct) out.pct = input.pct.map((v) => fmt.formatPctOfNormal(v))
if (input.estimate) out.estimate = input.estimate.map((c) => fmt.formatEstimate(c))
if (input.verdictProbability) out.verdictProbability = input.verdictProbability.map((c) => fmt.verdictProbability(c))
if (input.anomalyText) {
  out.anomalyText = input.anomalyText.map((a) => ({ pct: rankings.pctText(a), probability: rankings.probabilityText(a) }))
}
if (input.ranking) {
  const r = rankings.rankAnomalies(input.ranking.anomalies, input.ranking.tab)
  out.ranking = {
    above: r.above.map((a) => a.entity_id),
    below: r.below.map((a) => a.entity_id),
    notRanked: rankings.notRankedCount(input.ranking.total, r),
  }
}
if (input.statuses) out.statuses = validation.countStatuses(input.statuses)
if (input.bboxLabel) out.bboxLabel = input.bboxLabel.map((b) => bbox.bboxLabel(b))
if (input.measured) out.measured = input.measured.map((v) => validation.formatMeasured(v))

writeFileSync(outputPath, JSON.stringify(out))
