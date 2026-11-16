import { renderToString } from 'react-dom/server'
import { describe, expect, it } from 'vitest'
import { FEATURED_STORIES } from '../../content/featured.ts'
import type { FeaturedStory } from '../../content/featured.ts'
import { EXPLAINERS, START_HERE_LEDE, TOUR_STEPS, storyQuestion } from '../../content/help.ts'
import { GLOSSARY, HOW_TO_READ } from '../../content/plainLanguage.ts'
import * as UI from '../../content/ui.ts'
import { VERDICT_PRESENTATION } from '../../content/verdicts.ts'
import { HowToRead } from '../layout/HowToRead.tsx'
import { returnFocusTarget, trapIndex } from './focusTrap.ts'
import { HelpTip } from './HelpTip.tsx'
import { globeHintDue } from './hints.ts'
import { placeBeside, ringRect, spaceAround } from './placement.ts'
import { isMacPlatform, isTypingTarget, ownsArrows, ownsSpace, shortcutFor } from './shortcuts.ts'
import type { KeyPress, KeyTarget } from './shortcuts.ts'
import { START_HERE_COUNT, startHereExamples } from './startExamples.ts'
import { StartHere } from './StartHere.tsx'
import { TOUR_ORDER, tourAnchor, tourKey, tourReducer, tourSelector } from './tour.ts'
import type { TourState } from './tour.ts'

// The help layer of T-093. SYNTHETIC: no data are involved (the stories are the generated featured.ts).

const plain = (html: string) => html.replace(/<[^>]+>/g, '').replace(/&#x27;/g, "'").replace(/&quot;/g, '"').replace(/&amp;/g, '&')

describe('tour navigation', () => {
  const run = (actions: Parameters<typeof tourReducer>[1][]): TourState =>
    actions.reduce<TourState>((s, a) => tourReducer(s, a, 5), { step: 0 })

  it('goes forward and back through the five steps and finishes after the last', () => {
    expect(run([{ type: 'next' }])).toEqual({ step: 1 })
    expect(run([{ type: 'next' }, { type: 'next' }, { type: 'back' }])).toEqual({ step: 1 })
    expect(run([{ type: 'back' }])).toEqual({ step: 0 })
    expect(run(Array.from({ length: 4 }, () => ({ type: 'next' as const })))).toEqual({ step: 4 })
    expect(run(Array.from({ length: 5 }, () => ({ type: 'next' as const })))).toEqual({ closed: 'finished' })
  })

  it('closes on Skip at any step, and stays closed', () => {
    expect(run([{ type: 'next' }, { type: 'skip' }])).toEqual({ closed: 'skipped' })
    expect(run([{ type: 'skip' }, { type: 'next' }])).toEqual({ closed: 'skipped' })
  })

  it('maps Esc to Skip and the arrow keys to Back and Next inside the coach mark', () => {
    expect(tourKey('Escape')).toEqual({ type: 'skip' })
    expect(tourKey('ArrowRight')).toEqual({ type: 'next' })
    expect(tourKey('ArrowLeft')).toEqual({ type: 'back' })
    expect(tourKey('Enter')).toBeNull()
    expect(tourKey('Tab')).toBeNull()
  })
})

describe('tour anchors', () => {
  const box = (w: number, h: number) => ({ getBoundingClientRect: () => ({ width: w, height: h, top: 0, left: 0 }) }) as unknown as Element
  const doc = (present: Record<string, Element>) => ({
    querySelector: (sel: string) => Object.entries(present).find(([id]) => sel === tourSelector(id))?.[1] ?? null,
  })
  const why = TOUR_STEPS.find((s) => s.id === 'why')
  const place = TOUR_STEPS.find((s) => s.id === 'place')

  it('finds the step by its data-tour attribute', () => {
    const el = box(100, 30)
    expect(place).toBeDefined()
    if (place !== undefined) expect(tourAnchor(place, doc({ place: el }))).toBe(el)
    expect(tourSelector('raw')).toBe('[data-tour="raw"]')
  })

  it('falls back from the reasons to the verdict when the reasons are absent or hidden', () => {
    const verdict = box(380, 600)
    const reasons = box(300, 80)
    if (why === undefined) throw new Error('no why step')
    expect(tourAnchor(why, doc({ why: reasons, verdict }))).toBe(reasons)
    expect(tourAnchor(why, doc({ verdict }))).toBe(verdict)
    expect(tourAnchor(why, doc({ why: box(0, 0), verdict }))).toBe(verdict)
  })

  it('gives null (a centred coach mark) when nothing is on screen', () => {
    if (place !== undefined) expect(tourAnchor(place, doc({}))).toBeNull()
  })
})

describe('placement beside an element', () => {
  const view = { width: 1440, height: 900 }
  const coach = { width: 320, height: 180 }
  const order = ['right', 'left', 'bottom', 'top'] as const

  it('sits on the right of a control at the top left, inside the viewport, with the arrow on the control', () => {
    const anchor = { top: 20, left: 20, width: 270, height: 36 }
    const p = placeBeside(anchor, coach, view, { order, gap: 14, margin: 8 })
    expect(p.side).toBe('right')
    expect(p.left).toBe(20 + 270 + 14)
    expect(p.top).toBe(8)
    // The arrow points at the control's middle (y = 38), measured from the box's top.
    expect(p.arrow).toBe(30)
  })

  it('goes to the left of the answer panel at the right edge', () => {
    const anchor = { top: 44, left: 1060, width: 380, height: 856 }
    const p = placeBeside(anchor, coach, view, { order: TOUR_ORDER.verdict, gap: 14, margin: 8 })
    expect(p.side).toBe('left')
    expect(p.left).toBe(1060 - 14 - 320)
    expect(p.top + coach.height).toBeLessThanOrEqual(view.height - 8)
  })

  it('goes above a full-width strip at the bottom (the timeline), the order the tour gives that step', () => {
    const anchor = { top: 820, left: 0, width: 1060, height: 60 }
    const p = placeBeside(anchor, coach, view, { order: TOUR_ORDER.month, gap: 14, margin: 8 })
    expect(p.side).toBe('top')
    expect(p.top).toBe(820 - 14 - 180)
  })

  it('fits a phone: below the search when no side has room, kept inside the 375 px width', () => {
    const phone = { width: 375, height: 812 }
    const anchor = { top: 100, left: 12, width: 350, height: 36 }
    const p = placeBeside(anchor, { width: 359, height: 200 }, phone, { order, gap: 14, margin: 8 })
    expect(p.side).toBe('bottom')
    expect(p.left).toBeGreaterThanOrEqual(8)
    expect(p.left + 359).toBeLessThanOrEqual(375 - 8)
  })

  it('flips a popover above when it does not fit below', () => {
    const anchor = { top: 860, left: 700, width: 24, height: 24 }
    const p = placeBeside(anchor, { width: 288, height: 140 }, view, { order: ['bottom', 'top', 'right', 'left'], gap: 8 })
    expect(p.side).toBe('top')
    expect(p.top).toBe(860 - 8 - 140)
  })

  it('keeps a popover near the right edge inside the viewport, the arrow still on the "?"', () => {
    const anchor = { top: 100, left: 1420, width: 16, height: 16 }
    const p = placeBeside(anchor, { width: 288, height: 140 }, view, { order: ['bottom', 'top'], gap: 8, margin: 8 })
    expect(p.left).toBe(1440 - 8 - 288)
    expect(p.arrow).toBe(288 - 16)
  })

  it('centres the box without an element', () => {
    const p = placeBeside(null, coach, view, { order })
    expect(p.side).toBeNull()
    expect(p.left).toBe((1440 - 320) / 2)
  })

  it('measures the space on each side and keeps the ring on screen', () => {
    expect(spaceAround({ top: 10, left: 20, width: 100, height: 50 }, view)).toEqual({ top: 10, bottom: 840, left: 20, right: 1320 })
    expect(ringRect({ top: 0, left: 0, width: 1440, height: 900 }, view)).toEqual({ top: 2, left: 2, width: 1436, height: 896 })
    expect(ringRect({ top: 100, left: 100, width: 50, height: 20 }, view)).toEqual({ top: 96, left: 96, width: 58, height: 28 })
  })
})

describe('keyboard shortcuts', () => {
  const el = (tagName: string, attrs: Record<string, string> = {}, inside: string[] = []): KeyTarget => ({
    tagName,
    getAttribute: (n) => attrs[n] ?? null,
    closest: (sel) => (inside.includes(sel) ? {} : null),
  })
  const body = el('BODY')
  const press = (key: string, target: KeyTarget | null = body, mods: Partial<KeyPress> = {}): KeyPress => ({
    key,
    ctrlKey: false,
    metaKey: false,
    altKey: false,
    target,
    ...mods,
  })

  it('maps each key to its action', () => {
    expect(shortcutFor(press('ArrowLeft'))).toBe('month-prev')
    expect(shortcutFor(press('ArrowRight'))).toBe('month-next')
    expect(shortcutFor(press('PageDown'))).toBe('year-prev')
    expect(shortcutFor(press('PageUp'))).toBe('year-next')
    expect(shortcutFor(press(' '))).toBe('play')
    expect(shortcutFor(press('g'))).toBe('globe')
    expect(shortcutFor(press('G'))).toBe('globe')
    expect(shortcutFor(press('s'))).toBe('satellite')
    expect(shortcutFor(press('/'))).toBe('search')
    expect(shortcutFor(press('?'))).toBe('shortcuts')
    expect(shortcutFor(press('Escape'))).toBe('close')
    expect(shortcutFor(press('x'))).toBeNull()
    expect(shortcutFor(press('Enter'))).toBeNull()
  })

  it('does nothing while the user types in an input, a textarea, a select or an editable region', () => {
    for (const t of [el('INPUT'), el('TEXTAREA'), el('SELECT'), el('DIV', { contenteditable: 'true' }), el('DIV', { role: 'combobox' })]) {
      for (const k of ['g', 's', '/', '?', ' ', 'ArrowLeft', 'PageUp']) expect(shortcutFor(press(k, t)), `${t.tagName} ${k}`).toBeNull()
    }
    expect(isTypingTarget({ tagName: 'DIV', isContentEditable: true, getAttribute: () => null })).toBe(true)
    expect(isTypingTarget(el('BUTTON'))).toBe(false)
    expect(isTypingTarget(null)).toBe(false)
  })

  it('does nothing while Ctrl, Alt or Cmd is held (browser shortcuts stay the browser\'s)', () => {
    expect(shortcutFor(press('s', body, { ctrlKey: true }))).toBeNull()
    expect(shortcutFor(press('g', body, { metaKey: true }))).toBeNull()
    expect(shortcutFor(press('ArrowLeft', body, { altKey: true }))).toBeNull()
    expect(shortcutFor(press('Escape', body, { metaKey: true }))).toBeNull()
  })

  it('does nothing inside a dialog, except Esc', () => {
    const inDialog = el('BUTTON', {}, ['[role="dialog"]'])
    expect(shortcutFor(press('g', inDialog))).toBeNull()
    expect(shortcutFor(press('ArrowRight', inDialog))).toBeNull()
    expect(shortcutFor(press('?', inDialog))).toBeNull()
    expect(shortcutFor(press('Escape', inDialog))).toBe('close')
  })

  it('leaves the arrow keys to the map canvas, sliders, tabs and radio groups', () => {
    for (const t of [el('CANVAS'), el('DIV', { role: 'slider' }), el('BUTTON', { role: 'tab' }), el('DIV', {}, ['.maplibregl-canvas-container'])]) {
      expect(shortcutFor(press('ArrowLeft', t))).toBeNull()
      expect(shortcutFor(press('PageUp', t))).toBeNull()
    }
    expect(ownsArrows(el('BUTTON'))).toBe(false)
    // The other shortcuts still work there.
    expect(shortcutFor(press('g', el('CANVAS')))).toBe('globe')
  })

  it('leaves Space to a focused button, link, switch or summary', () => {
    for (const t of [el('BUTTON'), el('A'), el('SUMMARY'), el('DIV', { role: 'switch' })]) expect(shortcutFor(press(' ', t))).toBeNull()
    expect(ownsSpace(el('MAIN'))).toBe(false)
    expect(shortcutFor(press(' ', el('MAIN')))).toBe('play')
  })

  it('ignores a key another control already handled', () => {
    expect(shortcutFor(press('ArrowLeft', body, { defaultPrevented: true }))).toBeNull()
  })

  it('tells a Mac from other platforms for the zoom key', () => {
    expect(isMacPlatform('MacIntel')).toBe(true)
    expect(isMacPlatform('macOS')).toBe(true)
    expect(isMacPlatform('iPhone')).toBe(true)
    expect(isMacPlatform('Win32')).toBe(false)
    expect(isMacPlatform('Linux x86_64')).toBe(false)
  })
})

describe('focus', () => {
  it('wraps Tab and Shift+Tab at the ends of a dialog and leaves the middle to the browser', () => {
    expect(trapIndex(3, 2, false)).toBe(0)
    expect(trapIndex(3, 0, true)).toBe(2)
    expect(trapIndex(3, -1, false)).toBe(0)
    expect(trapIndex(3, -1, true)).toBe(2)
    expect(trapIndex(3, 1, false)).toBeNull()
    expect(trapIndex(3, 1, true)).toBeNull()
    expect(trapIndex(0, -1, false)).toBeNull()
  })

  it('returns focus to the control that opened the help, else to the Help button', () => {
    const body = { id: 'body' } as unknown as Element
    const help = { id: 'help' } as unknown as Element
    const opener = { id: 'opener' } as unknown as Element
    const gone = { id: 'gone' } as unknown as Element
    const doc = { body, contains: (n: Node) => (n as unknown) !== gone }
    expect(returnFocusTarget(opener, help, doc)).toBe(opener)
    expect(returnFocusTarget(body, help, doc)).toBe(help)
    expect(returnFocusTarget(null, help, doc)).toBe(help)
    expect(returnFocusTarget(gone, help, doc)).toBe(help)
  })
})

describe('the globe hint', () => {
  it('is due only when the user turns a flat map into a globe, outside the tour, the first time', () => {
    expect(globeHintDue('flat', 'globe', false, false)).toBe(true)
    expect(globeHintDue('globe', 'globe', false, false)).toBe(false)
    expect(globeHintDue('globe', 'flat', false, false)).toBe(false)
    expect(globeHintDue('flat', 'globe', true, false)).toBe(false)
    expect(globeHintDue('flat', 'globe', false, true)).toBe(false)
  })
})

describe('Start here', () => {
  it('takes three country stories from featured.ts, in their order', () => {
    const picked = startHereExamples(FEATURED_STORIES)
    expect(picked.length).toBe(START_HERE_COUNT)
    expect(picked.every((s) => s.entityType === 'COUNTRY')).toBe(true)
    expect(picked.map((s) => s.id)).toEqual(FEATURED_STORIES.filter((s) => s.entityType === 'COUNTRY').slice(0, 3).map((s) => s.id))
  })

  it('shows what the map answers, the questions built from the stories, search and the world, with no emoji', () => {
    const html = renderToString(<StartHere onChooseStory={() => {}} onSearch={() => {}} onShowWorld={() => {}} worldMonth="October 2026" />)
    const text = plain(html)
    expect(text).toContain(START_HERE_LEDE)
    for (const s of startHereExamples(FEATURED_STORIES)) expect(text).toContain(storyQuestion(s))
    expect(text).toContain('Search any country')
    expect(text).toContain('Show the whole world for October 2026')
    expect(html).toContain('aria-keyshortcuts="/"')
    expect(text).not.toMatch(/\p{Extended_Pictographic}/u)
    // Rows of a list, not a grid of cards.
    expect(html).toContain('<ul class="start-here-list"')
  })

  it('builds the questions from whatever stories it is given (SYNTHETIC story)', () => {
    const base = FEATURED_STORIES[0] as FeaturedStory
    const story: FeaturedStory = { ...base, id: 'synthetic', entityName: 'Testland', year: 2010, month: 3 }
    const text = plain(renderToString(<StartHere stories={[story]} onChooseStory={() => {}} onSearch={() => {}} onShowWorld={() => {}} worldMonth={null} />))
    expect(text).toContain("Was Testland's fire activity in March 2010 unusual?")
    expect(text).toContain('Show the whole world')
  })
})

describe('"?" explainer button', () => {
  it('is a named, closed disclosure with the instrument glyph', () => {
    const html = renderToString(<HelpTip term="pct-of-normal" />)
    expect(html).toContain('aria-label="What is % of normal?"')
    expect(html).toContain('aria-expanded="false"')
    expect(html).toContain('class="bare help-tip"')
    expect(html).toContain('help-tip-glyph')
    // The sentence is in the popover, not in a title tooltip.
    expect(html).not.toContain('title=')
    expect(EXPLAINERS['pct-of-normal'].text.length).toBeGreaterThan(0)
  })
})

describe('"How to read this" inside the Help sheet', () => {
  it('keeps the approved steps, verdicts and glossary word for word, without the old close button', () => {
    const html = renderToString(<HowToRead variant="sheet" />)
    const text = plain(html)
    for (const s of HOW_TO_READ) {
      expect(text).toContain(s.title)
      expect(text).toContain(s.text)
    }
    for (const g of GLOSSARY) expect(text).toContain(g.hint)
    for (const v of Object.values(VERDICT_PRESENTATION)) expect(text).toContain(v.description)
    expect(html).not.toContain(UI.HOW_TO_READ_CLOSE)
    expect(html).toContain('class="help-howto"')
    expect(html).not.toContain('class="how-to-read"')
  })
})
