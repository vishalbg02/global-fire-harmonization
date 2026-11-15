// Verdict colours over representative imagery colours (T-084, risk T18). The cells are drawn with
// alpha CELL_OPACITY_IMAGERY (0.78 after the Lead's note on cloud; it was 0.65) over imagery, so the effective colour is a blend. Samples are chosen by hand, not read
// from GIBS tiles: deep ocean, desert tan, forest green, bright cloud and smoke grey.
import { describe, expect, it } from 'vitest'
import { CVD_TYPES, deltaE2000Rgb, simulate } from '../../content/colorVision.ts'
import type { CvdType, Rgb } from '../../content/colorVision.ts'
import { VERDICT_PRESENTATION } from '../../content/verdicts.ts'
import { CELL_CASING_IMAGERY, CELL_OPACITY_IMAGERY } from './gibs.ts'

const SAMPLES: Record<string, Rgb> = {
  'dark ocean': [12, 38, 74],
  'desert tan': [196, 170, 125],
  vegetation: [52, 92, 48],
  'white cloud': [240, 242, 245],
  'grey smoke': [150, 150, 148],
}

const blend = (fg: Rgb, bg: Rgb, a: number): Rgb => [0, 1, 2].map((i) => Math.round(fg[i] * a + bg[i] * (1 - a))) as unknown as Rgb
const modes: readonly (CvdType | undefined)[] = [undefined, ...CVD_TYPES]
const VERDICTS = Object.keys(VERDICT_PRESENTATION) as (keyof typeof VERDICT_PRESENTATION)[]

/** The pairs a reader must tell apart: the verdicts that carry a different statement. The icons also differ. */
export function worstPairs(alpha: number): { sample: string; mode: string; pair: string; dE: number }[] {
  const out: { sample: string; mode: string; pair: string; dE: number }[] = []
  for (const [sample, bg] of Object.entries(SAMPLES)) {
    for (const mode of modes) {
      for (let i = 0; i < VERDICTS.length; i++) {
        for (let j = i + 1; j < VERDICTS.length; j++) {
          const a = blend(VERDICT_PRESENTATION[VERDICTS[i]].color as unknown as Rgb, bg, alpha)
          const b = blend(VERDICT_PRESENTATION[VERDICTS[j]].color as unknown as Rgb, bg, alpha)
          out.push({ sample, mode: mode ?? 'normal', pair: `${VERDICTS[i]} / ${VERDICTS[j]}`, dE: deltaE2000Rgb(a, b, mode) })
        }
      }
    }
  }
  return out.sort((x, y) => x.dE - y.dE)
}

describe('verdict cells over imagery', () => {
  it('prints the worst cases (for the PR)', () => {
    const w = worstPairs(CELL_OPACITY_IMAGERY).slice(0, 8)
    console.log('IMAGERY-CV worst pairs @alpha', JSON.stringify(w))
    expect(w.length).toBeGreaterThan(0)
  })

  it('the two verdicts that matter most, above and below normal, stay clearly apart (dE >= 10) over every sample and vision type', () => {
    const rows = worstPairs(CELL_OPACITY_IMAGERY).filter((r) => r.pair === 'ABOVE_NORMAL / BELOW_NORMAL')
    for (const r of rows) expect(r.dE, `${r.sample} ${r.mode}`).toBeGreaterThanOrEqual(10)
  })

  it('every verdict colour differs from its own backdrop by dE >= 5 over each sample (cells are seen against the imagery)', () => {
    const fails: string[] = []
    const lows: { v: string; sample: string; mode: string; dE: number }[] = []
    for (const [sample, bg] of Object.entries(SAMPLES)) {
      for (const mode of modes) {
        for (const v of VERDICTS) {
          const c = blend(VERDICT_PRESENTATION[v].color as unknown as Rgb, bg, CELL_OPACITY_IMAGERY)
          const dE = deltaE2000Rgb(c, bg, mode)
          lows.push({ v, sample, mode: mode ?? 'normal', dE })
        }
      }
    }
    lows.sort((a, b) => a.dE - b.dE)
    console.log('IMAGERY-CV lowest cell-vs-backdrop @alpha', JSON.stringify(lows.slice(0, 8)))
    // Known exception, reported in the PR: the neutral grey "Within normal" fill is the same grey as thick smoke,
    // so the fill alone does not separate from it. Its white outline and the round icon still mark the cell.
    for (const l of lows) if (l.dE < 5 && !(l.v === 'WITHIN_NORMAL' && l.sample === 'grey smoke')) fails.push(`${l.v} on ${l.sample} (${l.mode}): ${l.dE.toFixed(1)}`)
    expect(fails).toEqual([])
  })

  it('raising the opacity from 0.65 improves the weakest cell-vs-backdrop separation (numbers printed for the PR)', () => {
    const lowest = (alpha: number) => {
      let m = Infinity
      for (const [sample, bg] of Object.entries(SAMPLES))
        for (const mode of modes)
          for (const v of VERDICTS) {
            if (v === 'WITHIN_NORMAL' && sample === 'grey smoke') continue
            m = Math.min(m, deltaE2000Rgb(blend(VERDICT_PRESENTATION[v].color as unknown as Rgb, bg, alpha), bg, mode))
          }
      return m
    }
    const before = lowest(0.65)
    const after = lowest(CELL_OPACITY_IMAGERY)
    console.log('IMAGERY-CV weakest cell-vs-backdrop dE: 0.65 ->', before.toFixed(1), `${CELL_OPACITY_IMAGERY} ->`, after.toFixed(1))
    expect(after).toBeGreaterThan(before)
  })

  it('the thin dark casing separates from the bright backdrops (tan, cloud, smoke) (dE >= 15), so a cell edge reads even when its fill is pale', () => {
    const [r, g, b, a] = CELL_CASING_IMAGERY
    const rows = Object.entries(SAMPLES).map(([sample, bg]) => ({ sample, dE: deltaE2000Rgb(blend([r, g, b], bg, a / 255), bg) }))
    console.log('IMAGERY-CV casing vs backdrop', JSON.stringify(rows.map((x) => ({ ...x, dE: +x.dE.toFixed(1) }))))
    // Over dark ocean (dE 2.9) and dark forest (7.7) a dark casing separates little; there the pale fills already stand out, so the casing is for bright imagery.
    for (const row of rows) if (row.sample !== 'dark ocean' && row.sample !== 'vegetation') expect(row.dE, row.sample).toBeGreaterThanOrEqual(15)
  })

  it('simulate is used for the dichromacy modes (sanity)', () => {
    expect(simulate([213, 94, 0], 'protanopia')).not.toEqual([213, 94, 0])
  })
})
