import type { CSSProperties } from 'react'
import './states.css'

export function LoadingState({ what }: { what: string }) {
  return (
    <p className="state state-loading" role="status">
      {`Loading ${what}…`}
    </p>
  )
}

/** An error message; the Retry button only appears when retrying can help (`onRetry` given). */
export function ErrorState({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <div className="state state-error" role="alert">
      <p>{message}</p>
      {onRetry !== undefined && (
        <button type="button" onClick={onRetry}>
          Retry
        </button>
      )}
    </div>
  )
}

export function EmptyState({ message }: { message: string }) {
  return <p className="state state-empty">{message}</p>
}

/** One grey block of a skeleton: a height in pixels and a width (a CSS length, 100% by default). */
export interface SkeletonBlock {
  h: number
  w?: string
  /** Space above the block, in pixels. */
  gap?: number
}

/**
 * A loading placeholder shaped like what is coming, so nothing moves when it arrives (no spinner inside text). Screen
 * readers hear "Loading <what>…" once; the grey blocks are hidden from them.
 */
export function Skeleton({ what, blocks, className }: { what: string; blocks: readonly SkeletonBlock[]; className?: string }) {
  return (
    <div className={`skeleton${className === undefined ? '' : ` ${className}`}`} role="status">
      <span className="visually-hidden">{`Loading ${what}…`}</span>
      {blocks.map((b, i) => (
        <span
          key={i}
          className="skeleton-block"
          aria-hidden="true"
          style={{ height: `${b.h}px`, width: b.w ?? '100%', marginTop: `${b.gap ?? 0}px` } as CSSProperties}
        />
      ))}
    </div>
  )
}
