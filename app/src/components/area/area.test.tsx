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
import { CustomAreaPanel } from './CustomAreaPanel.tsx'
import { areaFitBbox } from './resolveArea.ts'
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

const picker = (overrides: Partial<Parameters<typeof CustomAreaPanel>[0]> = {}) =>
  renderToString(
    <CustomAreaPanel
      area={WORLD}
      onChooseCustom={() => {}}
      drawing={false}
      onToggleDrawing={() => {}}
      customMessage={null}
      customLoading={false}
      {...overrides}
    />,
  )

describe('CustomAreaPanel (the "Draw or type an area" panel)', () => {
  it('holds the custom rectangle form with its messages, unchanged', () => {
    const html = picker()
    expect(html).toContain('Custom area')
    expect(html).toContain('Show custom area')
    expect(html).toContain('Draw on the map')
  })

  it('fills the custom fields from the current custom area', () => {
    const html = picker({ area: customArea([100, 0, 101.5, 1]) })
    expect(html).toContain('value="100"')
    expect(html).toContain('value="101.5"')
  })

  it('has the polygon route when it is given', () => {
    const html = picker({ polygon: { onSubmit: () => {}, drawing: false, onToggleDrawing: () => {}, cells: null } })
    expect(html).toContain('Show polygon')
    expect(html).toContain('Draw a polygon on the map')
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

  it('says that a new area is being computed, and can take several seconds, while it loads (T-042)', () => {
    expect(form({ loading: true })).toContain('A new area can take several seconds.')
    expect(form({ loading: true })).toContain('aria-busy="true"')
    expect(form({ loading: false })).not.toContain('Computing this area')
  })

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

describe('the box the map shows for the selected area (T-039 review)', () => {
  const countries: EntityItem[] = [
    { entity_type: 'COUNTRY', entity_id: 'AUS', entity_name: 'Australia', bbox: [112, -44, 154, -10] },
  ]
  const continents: EntityItem[] = [
    { entity_type: 'CONTINENT', entity_id: 'OC', entity_name: 'Oceania', bbox: [110, -50, 180, 0] },
  ]
  it('is the entity box for a country or a continent, however it was chosen (also from a link)', () => {
    const aus: Area = { entity_type: 'COUNTRY', entity_id: 'AUS', entity_name: 'AUS' }
    const oc: Area = { entity_type: 'CONTINENT', entity_id: 'OC', entity_name: 'OC' }
    expect(areaFitBbox(aus, countries, continents)).toEqual([112, -44, 154, -10])
    expect(areaFitBbox(oc, countries, continents)).toEqual([110, -50, 180, 0])
  })

  it('is the box of a custom area, and null for the world, a cell or a list that is not loaded yet', () => {
    expect(areaFitBbox(customArea([10, 20, 30, 40]), countries, continents)).toEqual([10, 20, 30, 40])
    expect(areaFitBbox(WORLD, countries, continents)).toBeNull()
    expect(areaFitBbox({ entity_type: 'COUNTRY', entity_id: 'AUS', entity_name: 'AUS' }, undefined, undefined)).toBeNull()
    expect(areaFitBbox({ entity_type: 'COUNTRY', entity_id: 'ZZZ', entity_name: 'ZZZ' }, countries, continents)).toBeNull()
  })
})
