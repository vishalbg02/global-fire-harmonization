import type { ReasonCode } from '../../api/contract.ts'

/** Opens a closed chip and closes an open one; the others keep their state. */
export function toggleReason(open: readonly ReasonCode[], code: ReasonCode): ReasonCode[] {
  return open.includes(code) ? open.filter((c) => c !== code) : [...open, code]
}
