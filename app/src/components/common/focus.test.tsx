import { isValidElement } from 'react'
import type { ReactElement } from 'react'
import { renderToString } from 'react-dom/server'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { HOW_TO_TOGGLE_ID, Header } from '../layout/Header.tsx'
import { HowToRead } from '../layout/HowToRead.tsx'
import { DRAW_MENU_BUTTON_ID, focusLater } from './focus.ts'

// Keyboard and focus helpers (T-074). SYNTHETIC: no data are involved.
afterEach(() => vi.unstubAllGlobals())

describe('focusLater', () => {
  it('focuses the element with the id after the next paint', () => {
    const focus = vi.fn()
    const doc = { getElementById: (id: string) => (id === 'a' ? { focus } : null) } as unknown as Document
    vi.stubGlobal('requestAnimationFrame', (cb: () => void) => cb())
    focusLater('a', doc)
    expect(focus).toHaveBeenCalledTimes(1)
  })

  it('does nothing when the element is gone, and never throws', () => {
    const doc = { getElementById: () => null } as unknown as Document
    vi.stubGlobal('requestAnimationFrame', (cb: () => void) => cb())
    expect(() => focusLater('missing', doc)).not.toThrow()
  })

  it('falls back to a timer when there is no animation frame', () => {
    vi.useFakeTimers()
    const focus = vi.fn()
    const doc = { getElementById: () => ({ focus }) } as unknown as Document
    vi.stubGlobal('requestAnimationFrame', undefined)
    focusLater('a', doc)
    expect(focus).not.toHaveBeenCalled()
    vi.runAllTimers()
    expect(focus).toHaveBeenCalledTimes(1)
    vi.useRealTimers()
  })
})

describe('the ids focus returns to', () => {
  it('the Help button carries the id the app hands focus back to', () => {
    const html = renderToString(<Header showMethods onOpenMethods={() => {}} helpOpen onHelp={() => {}} />)
    expect(html).toContain(`id="${HOW_TO_TOGGLE_ID}"`)
  })

  it('the draw button id is a plain, stable id', () => {
    expect(DRAW_MENU_BUTTON_ID).toMatch(/^[a-z-]+$/)
  })
})

describe('Esc in the "How to read this" panel', () => {
  const section = (onEscape?: () => void): ReactElement<{ onKeyDown: (e: { key: string }) => void }> => {
    const el = HowToRead({ onClose: () => {}, onEscape })
    if (!isValidElement(el)) throw new Error('not an element')
    return el as ReactElement<{ onKeyDown: (e: { key: string }) => void }>
  }

  it('calls the Esc handler for Escape only', () => {
    const onEscape = vi.fn()
    const el = section(onEscape)
    el.props.onKeyDown({ key: 'a' })
    expect(onEscape).not.toHaveBeenCalled()
    el.props.onKeyDown({ key: 'Escape' })
    expect(onEscape).toHaveBeenCalledTimes(1)
  })

  it('is harmless without a handler', () => {
    expect(() => section().props.onKeyDown({ key: 'Escape' })).not.toThrow()
  })
})
