import { describe, expect, it } from 'vitest'

// Confirms the approved libraries are installed and resolvable (not used yet).
describe('approved stack is installed', () => {
  it.each([
    'maplibre-gl',
    'deck.gl',
    'terra-draw',
    'echarts',
    '@tanstack/react-query',
  ])('resolves %s', (spec) => {
    expect(() => import.meta.resolve(spec)).not.toThrow()
  })
})
