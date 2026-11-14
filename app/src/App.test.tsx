import { renderToString } from 'react-dom/server'
import { describe, expect, it } from 'vitest'
import { SyntheticBanner } from './components/common/SyntheticBanner.tsx'

describe('synthetic banner', () => {
  it('is shown, with the required text, when metadata.synthetic is true', () => {
    const html = renderToString(<SyntheticBanner synthetic={true} />)
    expect(html).toContain('SYNTHETIC DATA — not NASA observations')
  })

  it('is not shown when metadata.synthetic is false', () => {
    expect(renderToString(<SyntheticBanner synthetic={false} />)).toBe('')
  })
})
