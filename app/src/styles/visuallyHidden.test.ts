import { readFileSync } from 'node:fs'
import { describe, expect, it } from 'vitest'

// T-088: a hidden <table> ignores width and overflow unless it is a block, which made the page 1693 px wide at 1440.
const css = readFileSync(new URL('../index.css', import.meta.url), 'utf8')

/** The declaration block of every rule whose whole selector is `selector` (plain string search, no regular expression). */
function declarationBlocks(selector: string): string[] {
  const blocks: string[] = []
  for (const chunk of css.split('}')) {
    const open = chunk.lastIndexOf('{')
    if (open === -1) continue
    const header = chunk.slice(0, open).split('\n').pop()?.trim() ?? ''
    if (header === selector) blocks.push(chunk.slice(open + 1))
  }
  return blocks
}

describe('.visually-hidden (T-088)', () => {
  it('is defined once, with every property that takes an element out of the layout', () => {
    const found = declarationBlocks('.visually-hidden')
    expect(found).toHaveLength(1)
    for (const declaration of [
      'position: absolute',
      'width: 1px',
      'height: 1px',
      'margin: -1px',
      'padding: 0',
      'border: 0',
      'overflow: hidden',
      'clip: rect(0 0 0 0)',
      'clip-path: inset(50%)',
      'white-space: nowrap',
    ]) {
      expect(found[0]).toContain(declaration)
    }
  })

  it('makes a table a block, because a table ignores width and overflow (the cause of the sideways scroll)', () => {
    const found = declarationBlocks('table.visually-hidden')
    expect(found).toHaveLength(1)
    expect(found[0]).toContain('display: block')
  })
})
