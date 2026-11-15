/** The active option after an arrow key (wraps). -1 means none. */
export function moveActive(active: number, count: number, key: 'ArrowDown' | 'ArrowUp'): number {
  if (count === 0) return -1
  if (key === 'ArrowDown') return active < 0 ? 0 : (active + 1) % count
  return active < 0 ? count - 1 : (active - 1 + count) % count
}
