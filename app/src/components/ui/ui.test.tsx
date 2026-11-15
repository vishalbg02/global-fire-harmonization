import { renderToString } from 'react-dom/server'
import { describe, expect, it } from 'vitest'
import { Badge } from './Badge.tsx'
import { Button } from './Button.tsx'
import { Card } from './Card.tsx'
import { Chip } from './Chip.tsx'
import { Combobox } from './Combobox.tsx'
import { moveActive } from './comboKeys.ts'
import { SegmentedControl } from './SegmentedControl.tsx'
import { Tabs } from './Tabs.tsx'
import { nextTabIndex } from './tabKeys.ts'

describe('Button, Chip, Card, Badge', () => {
  it('Button defaults to a secondary type=button and takes a variant', () => {
    expect(renderToString(<Button>Go</Button>)).toMatch(/type="button"[^>]*class="btn btn-secondary"|class="btn btn-secondary"[^>]*type="button"/)
    expect(renderToString(<Button variant="primary">Go</Button>)).toContain('btn-primary')
  })
  it('Chip exposes its state with aria-pressed', () => {
    expect(renderToString(<Chip selected>A</Chip>)).toContain('aria-pressed="true"')
    expect(renderToString(<Chip>A</Chip>)).toContain('aria-pressed="false"')
  })
  it('Card is a flat section', () => {
    expect(renderToString(<Card aria-label="x">c</Card>)).toContain('<section class="card"')
  })
  it('Badge hides the icon from screen readers and keeps the label', () => {
    const html = renderToString(
      <Badge tone="ABOVE_NORMAL" icon="▲">
        Above normal
      </Badge>,
    )
    expect(html).toContain('aria-hidden="true"')
    expect(html).toContain('Above normal')
    expect(html).toContain('badge-above')
  })
})

describe('SegmentedControl', () => {
  const html = renderToString(
    <SegmentedControl
      legend="Data shown"
      name="d"
      value="raw"
      onChange={() => {}}
      options={[
        { value: 'raw', label: 'Raw' },
        { value: 'harmonized', label: 'Harmonized', disabled: true, describedBy: 'why' },
      ]}
    />,
  )
  it('is a named radio group with the checked option', () => {
    expect(html).toContain('<legend>Data shown</legend>')
    expect(html).toMatch(/<input[^>]*checked=""[^>]*value="raw"/)
  })
  it('keeps a disabled option focusable with aria-disabled and its reason', () => {
    expect(html).toContain('aria-disabled="true"')
    expect(html).toContain('aria-describedby="why"')
    expect(html).not.toMatch(/<input[^>]*\sdisabled/)
  })
})

describe('Tabs', () => {
  it('moves with the arrow keys, wraps, and supports Home and End', () => {
    expect(nextTabIndex(0, 4, 'ArrowRight')).toBe(1)
    expect(nextTabIndex(3, 4, 'ArrowRight')).toBe(0)
    expect(nextTabIndex(0, 4, 'ArrowLeft')).toBe(3)
    expect(nextTabIndex(2, 4, 'Home')).toBe(0)
    expect(nextTabIndex(1, 4, 'End')).toBe(3)
    expect(nextTabIndex(1, 4, 'a')).toBeNull()
    expect(nextTabIndex(0, 0, 'ArrowRight')).toBeNull()
  })
  it('renders the ARIA tabs pattern with one tab stop and only the selected panel', () => {
    const html = renderToString(
      <Tabs
        idBase="t"
        label="Details"
        value="b"
        onChange={() => {}}
        tabs={[
          { id: 'a', label: 'A', panel: <p>panel a</p> },
          { id: 'b', label: 'B', panel: <p>panel b</p> },
        ]}
      />,
    )
    expect(html).toContain('role="tablist"')
    expect(html).toContain('aria-label="Details"')
    expect(html).toMatch(/id="t-tab-b"[^>]*aria-selected="true"|aria-selected="true"[^>]*id="t-tab-b"/)
    expect(html.match(/tabindex="0"/g)?.length).toBe(2) // the selected tab and the panel
    expect(html).toContain('panel b')
    expect(html).not.toContain('panel a')
    expect(html).toContain('aria-labelledby="t-tab-b"')
  })
})

describe('Combobox', () => {
  it('moves the active option with the arrow keys and wraps', () => {
    expect(moveActive(-1, 3, 'ArrowDown')).toBe(0)
    expect(moveActive(2, 3, 'ArrowDown')).toBe(0)
    expect(moveActive(-1, 3, 'ArrowUp')).toBe(2)
    expect(moveActive(0, 3, 'ArrowUp')).toBe(2)
    expect(moveActive(0, 0, 'ArrowDown')).toBe(-1)
  })
  const props = {
    id: 'c',
    label: 'Area',
    value: '',
    getOptions: (q: string) =>
      [
        { id: 'BRA', label: 'Brazil', hint: 'Country' },
        { id: 'BRN', label: 'Brunei', hint: 'Country' },
      ].filter((o) => o.label.toLowerCase().startsWith(q.toLowerCase())),
    onSelect: () => {},
    noMatchText: (q: string) => `No match for ${q}`,
    resultsText: (n: number) => `${n} found`,
  }
  it('is closed at first, with the combobox attributes', () => {
    const html = renderToString(<Combobox {...props} />)
    expect(html).toContain('role="combobox"')
    expect(html).toContain('aria-expanded="false"')
    expect(html).toContain('aria-autocomplete="list"')
    expect(html).not.toContain('aria-activedescendant')
  })
  it('open: lists the options, points aria-activedescendant at the first, announces the count', () => {
    const html = renderToString(<Combobox {...props} initialOpen initialQuery="br" />)
    expect(html).toContain('aria-expanded="true"')
    expect(html).toContain('aria-activedescendant="c-opt-0"')
    expect(html).toContain('role="listbox"')
    expect(html.match(/role="option"/g)?.length).toBe(2)
    expect(html).toMatch(/id="c-opt-0"[^>]*aria-selected="true"|aria-selected="true"[^>]*id="c-opt-0"/)
    expect(html).toContain('2 found')
  })
  it('open with no match: says so and has no active option', () => {
    const html = renderToString(<Combobox {...props} initialOpen initialQuery="zz" />)
    expect(html).toContain('No match for zz')
    expect(html).not.toContain('aria-activedescendant')
  })
})
