import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { createRef } from 'react'
import { renderToString } from 'react-dom/server'
import { describe, expect, it } from 'vitest'
import type { EntityItem } from '../../api/contract.ts'
import { customArea } from '../../state/bbox.ts'
import { WORLD } from '../../state/selection.ts'
import type { Area } from '../../state/selection.ts'
import { CalendarPanel } from '../calendar/CalendarPanel.tsx'
import { ErrorState } from '../common/States.tsx'
import { EvidencePanel } from '../evidence/EvidencePanel.tsx'
import { AreaPicker } from './AreaPicker.tsx'
import { CustomAreaForm, GRID_NOTE } from './CustomAreaForm.tsx'
import { filterEntities, matchEntity } from './countryFilter.ts'
import { resolveArea } from './resolveArea.ts'

// SYNTHETIC test data. Not NASA observations.
const COUNTRIES: EntityItem[] = [
  { entity_type: 'COUNTRY', entity_id: 'BRA', entity_name: 'Brazil', bbox: [-56, -12, -53, -9.5] },
  { entity_type: 'COUNTRY', entity_id: 'IDN', entity_name: 'Indonesia', bbox: [95, -11, 141, 6] },
  { entity_type: 'COUNTRY', entity_id: 'COD', entity_name: 'Democratic Republic of the Congo', bbox: [20, -8, 30, 2] },
]
const CONTINENTS: EntityItem[] = [
  { entity_type: 'CONTINENT', entity_id: 'AS', entity_name: 'Asia', bbox: [95, -11, 141, 6] },
  { entity_type: 'CONTINENT', entity_id: 'SA', entity_name: 'South America', bbox: [-56, -12, -53, -9.5] },
]

describe('country filter', () => {
  it('matches a country by name, ignoring case and spaces', () => {
    expect(matchEntity(COUNTRIES, 'brazil')?.entity_id).toBe('BRA')
    expect(matchEntity(COUNTRIES, '  INDONESIA ')?.entity_id).toBe('IDN')
  })

  it('does not match a partial name or an empty text', () => {
    expect(matchEntity(COUNTRIES, 'Braz')).toBeNull()
    expect(matchEntity(COUNTRIES, '')).toBeNull()
    expect(matchEntity([], 'Brazil')).toBeNull()
  })

  it('filters by a part of the name, case-insensitively, and returns everything for empty text', () => {
    expect(filterEntities(COUNTRIES, 'CONGO').map((e) => e.entity_id)).toEqual(['COD'])
    expect(filterEntities(COUNTRIES, 'ia').map((e) => e.entity_id)).toEqual(['IDN'])
    expect(filterEntities(COUNTRIES, '')).toHaveLength(3)
    expect(filterEntities(COUNTRIES, 'zzz')).toEqual([])
  })
})

describe('resolveArea', () => {
  it('fills in the name of a country or continent that came from a link', () => {
    const fromLink: Area = { entity_type: 'COUNTRY', entity_id: 'BRA', entity_name: 'BRA' }
    expect(resolveArea(fromLink, COUNTRIES, CONTINENTS).entity_name).toBe('Brazil')
    const continent: Area = { entity_type: 'CONTINENT', entity_id: 'AS', entity_name: 'AS' }
    expect(resolveArea(continent, COUNTRIES, CONTINENTS).entity_name).toBe('Asia')
  })

  it('leaves an unknown id, the world, a custom area and a missing list unchanged', () => {
    const unknown: Area = { entity_type: 'COUNTRY', entity_id: 'RUS', entity_name: 'Russia' }
    expect(resolveArea(unknown, COUNTRIES, CONTINENTS)).toBe(unknown)
    expect(resolveArea(WORLD, COUNTRIES, CONTINENTS)).toBe(WORLD)
    const custom = customArea([0, 0, 1, 1])
    expect(resolveArea(custom, COUNTRIES, CONTINENTS)).toBe(custom)
    expect(resolveArea(unknown, undefined, undefined)).toBe(unknown)
  })
})

const picker = (overrides: Partial<Parameters<typeof AreaPicker>[0]> = {}) =>
  renderToString(
    <AreaPicker
      area={WORLD}
      countries={COUNTRIES}
      continents={CONTINENTS}
      listsFailed={false}
      onChooseEntity={() => {}}
      onChooseWorld={() => {}}
      onChooseCustom={() => {}}
      drawing={false}
      onToggleDrawing={() => {}}
      customMessage={null}
      customLoading={false}
      {...overrides}
    />,
  )

describe('AreaPicker', () => {
  it('offers the world, a labelled country search with its options, a continent choice and a custom area', () => {
    const html = picker()
    expect(html).toContain('World')
    expect(html).toMatch(/<label[^>]*>Country<\/label>/)
    expect(html).toMatch(/<input[^>]*list="[^"]*-countries"/)
    for (const c of COUNTRIES) expect(html).toContain(`<option value="${c.entity_name}"`)
    expect(html).toMatch(/<label[^>]*>Continent<\/label>/)
    for (const c of CONTINENTS) expect(html).toContain(`>${c.entity_name}</option>`)
    expect(html).toContain('Custom area')
  })

  it('says which area is shown, and shows the selected country in the search box', () => {
    const area: Area = { entity_type: 'COUNTRY', entity_id: 'BRA', entity_name: 'Brazil' }
    const html = picker({ area })
    expect(html).toContain('Showing: Brazil')
    expect(html).toMatch(/<input[^>]*value="Brazil"/)
  })

  it('marks the world as pressed only when it is the area', () => {
    expect(picker()).toContain('aria-pressed="true"')
    expect(picker({ area: { entity_type: 'COUNTRY', entity_id: 'BRA', entity_name: 'Brazil' } })).toContain('aria-pressed="false"')
  })

  it('selects the current continent in the continent choice', () => {
    const html = picker({ area: { entity_type: 'CONTINENT', entity_id: 'AS', entity_name: 'Asia' } })
    expect(html).toMatch(/<option value="AS" selected/)
  })

  it('says so when the lists could not be loaded, and still offers the world and a custom area', () => {
    const html = picker({ countries: undefined, continents: undefined, listsFailed: true })
    expect(html).toContain('could not be loaded')
    expect(html).toContain('role="alert"')
    expect(html).toContain('Show custom area')
  })

  it('fills the custom fields from the current custom area', () => {
    const html = picker({ area: customArea([100, 0, 101.5, 1]) })
    expect(html).toContain('value="100"')
    expect(html).toContain('value="101.5"')
  })
})

describe('CustomAreaForm', () => {
  const form = (overrides: Partial<Parameters<typeof CustomAreaForm>[0]> = {}) =>
    renderToString(
      <CustomAreaForm
        initial={null}
        onSubmit={() => {}}
        drawing={false}
        onToggleDrawing={() => {}}
        serverMessage={null}
        loading={false}
        {...overrides}
      />,
    )

  it('has four labelled fields with units, and the grid-cell note', () => {
    const html = form()
    for (const label of ['West (degrees)', 'South (degrees)', 'East (degrees)', 'North (degrees)']) {
      expect(html).toContain(label)
    }
    expect(html).toContain('Custom areas are approximated by the grid cells whose centres fall inside the box.')
    expect(GRID_NOTE).toBe('Custom areas are approximated by the grid cells whose centres fall inside the box.')
  })

  it('has a submit button and a draw button, and explains that drawing needs a pointer', () => {
    expect(form()).toContain('Show custom area')
    expect(form()).toContain('Draw on the map')
    const drawing = form({ drawing: true })
    expect(drawing).toContain('Cancel drawing')
    expect(drawing).toContain('aria-pressed="true"')
    expect(drawing).toContain('Drawing needs a pointer; use the fields above to enter a box with the keyboard.')
  })

  it('shows the server message (a 422 or a 503) as received', () => {
    const html = form({ serverMessage: 'No analysis cells have their centre inside this area.' })
    expect(html).toContain('No analysis cells have their centre inside this area.')
  })

  it('escapes a server message instead of treating it as markup', () => {
    const html = form({ serverMessage: '<img src=x onerror=alert(1)>' })
    expect(html).not.toContain('<img')
    expect(html).toContain('&lt;img')
  })

  it('disables the submit button while the custom area is loading', () => {
    expect(form({ loading: true })).toMatch(/<button[^>]*disabled[^>]*>Show custom area/)
  })
})

describe('a custom area in the calendar and the evidence panel', () => {
  const custom = customArea([100, 0, 101, 1])
  const wrap = (node: React.ReactNode) =>
    renderToString(<QueryClientProvider client={new QueryClient()}>{node}</QueryClientProvider>)

  it('names the custom area in the calendar heading', () => {
    const html = wrap(
      <CalendarPanel
        area={custom}
        meta={null}
        selectedMonth={null}
        valueMode="pct"
        source="harmonized"
        onValueModeChange={() => {}}
        onSelectMonth={() => {}}
        onShowWorld={() => {}}
      />,
    )
    expect(html).toContain('Calendar: Custom area')
    expect(html).toContain('Show the world')
  })

  it('shows the custom area and its box in the evidence panel, and asks the series, not the evidence endpoint', () => {
    const html = wrap(
      <EvidencePanel
        area={custom}
        month={{ year: 2015, month: 9 }}
        cell={null}
        meta={null}
        headingRef={createRef<HTMLHeadingElement>()}
        onShowWorld={() => {}}
      />,
    )
    expect(html).toContain('Evidence: Custom area, September 2015')
    expect(html).toContain('W 100.00, S 0.00, E 101.00, N 1.00')
    expect(html).toContain('Loading the evidence')
  })
})


describe('ErrorState retry', () => {
  it('shows Retry only when retrying can help', () => {
    expect(renderToString(<ErrorState message="Down." onRetry={() => {}} />)).toContain('Retry')
    const html = renderToString(<ErrorState message="No analysis cells have their centre inside this area." />)
    expect(html).not.toContain('Retry')
    expect(html).toContain('role="alert"')
  })
})
