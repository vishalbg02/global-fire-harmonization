import { renderToString } from 'react-dom/server'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { TOAST_CSV_DOWNLOADED, TOAST_MS } from '../../content/answer.ts'
import { LINK_COPIED } from '../../content/ui.ts'
import { runExport } from '../export/exportHelpers.ts'
import { copyAndConfirm } from '../layout/copyLink.ts'
import { Skeleton } from './States.tsx'
import { ToastHost } from './Toast.tsx'
import { createToastStore } from './toastStore.ts'

afterEach(() => vi.useRealTimers())

describe('toast store (T-093)', () => {
  it('shows a toast and hides it by itself after about 3 s', () => {
    vi.useFakeTimers()
    const store = createToastStore()
    const seen: (string | null)[] = []
    store.subscribe(() => seen.push(store.get()?.message ?? null))
    store.show(LINK_COPIED)
    expect(store.get()?.message).toBe(LINK_COPIED)
    expect(TOAST_MS).toBe(3000)
    vi.advanceTimersByTime(TOAST_MS - 1)
    expect(store.get()).not.toBeNull()
    vi.advanceTimersByTime(1)
    expect(store.get()).toBeNull()
    expect(seen).toEqual([LINK_COPIED, null])
  })

  it('keeps one toast at a time: a new one replaces the old and restarts the clock', () => {
    vi.useFakeTimers()
    const store = createToastStore()
    store.show(LINK_COPIED)
    const first = store.get()!.id
    vi.advanceTimersByTime(2000)
    store.show(TOAST_CSV_DOWNLOADED)
    expect(store.get()).toEqual({ id: first + 1, message: TOAST_CSV_DOWNLOADED })
    vi.advanceTimersByTime(2000)
    expect(store.get()?.message).toBe(TOAST_CSV_DOWNLOADED)
    vi.advanceTimersByTime(1000)
    expect(store.get()).toBeNull()
  })

  it('gives the same message a new id, so it is announced again', () => {
    const store = createToastStore()
    store.show(LINK_COPIED)
    const a = store.get()!.id
    store.show(LINK_COPIED)
    expect(store.get()!.id).toBe(a + 1)
    store.hide()
  })

  it('can be hidden early, and stops telling a listener that left', () => {
    vi.useFakeTimers()
    const store = createToastStore()
    const listener = vi.fn()
    const leave = store.subscribe(listener)
    store.show(LINK_COPIED)
    store.hide()
    expect(store.get()).toBeNull()
    expect(listener).toHaveBeenCalledTimes(2)
    leave()
    store.show(LINK_COPIED)
    expect(listener).toHaveBeenCalledTimes(2)
    vi.runAllTimers()
  })
})

describe('toast host', () => {
  it('is one polite live region that is always in the page', () => {
    const empty = renderToString(<ToastHost store={createToastStore()} />)
    expect(empty).toContain('role="status"')
    expect(empty).toContain('aria-live="polite"')
    expect(empty).toContain('aria-atomic="true"')
    expect(empty).not.toContain('class="toast"')
  })
})

describe('the actions confirm with a toast', () => {
  it('"Link copied" only when the link was copied', async () => {
    const notify = vi.fn()
    expect(await copyAndConfirm('http://x/?a=1', notify, { clipboard: { writeText: async () => {} } })).toBe(true)
    expect(notify).toHaveBeenCalledWith(LINK_COPIED)
    notify.mockClear()
    const refused = { writeText: async () => Promise.reject(new Error('denied')) }
    expect(await copyAndConfirm('http://x/', notify, { clipboard: refused, legacy: () => false })).toBe(false)
    expect(notify).not.toHaveBeenCalled()
  })

  it('"CSV downloaded" after the file is handed to the browser, and no toast on a failure', async () => {
    const order: string[] = []
    const blob = new Blob(['a'])
    const ok = await runExport('IDN', false, {
      download: async () => ({ blob, filename: 'x.csv' }),
      save: (_b, name) => void order.push(`save ${name}`),
      notify: (m) => void order.push(`notify ${m}`),
    })
    expect(ok).toEqual({ ok: true })
    expect(order).toEqual(['save x.csv', `notify ${TOAST_CSV_DOWNLOADED}`])
    const notify = vi.fn()
    const failed = await runExport('IDN', false, {
      download: async () => Promise.reject(new Error('x')),
      save: () => {},
      notify,
    })
    expect(failed).toEqual({ ok: false, message: 'The CSV could not be created.' })
    expect(notify).not.toHaveBeenCalled()
  })
})

describe('skeleton', () => {
  it('says what is loading once to screen readers and hides its grey blocks from them', () => {
    const html = renderToString(<Skeleton what="the analytics" blocks={[{ h: 18, w: '30%' }, { h: 260, gap: 8 }]} />)
    expect(html).toContain('role="status"')
    expect(html).toContain('Loading the analytics…')
    expect(html.split('aria-hidden="true"').length - 1).toBe(2)
    expect(html).toContain('height:260px')
    expect(html).toContain('margin-top:8px')
  })
})
