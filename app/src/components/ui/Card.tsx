import type { HTMLAttributes } from 'react'

/** A flat panel: 1 px rule, no shadow. */
export function Card({ className, ...rest }: HTMLAttributes<HTMLElement>) {
  return <section className={`card${className === undefined ? '' : ` ${className}`}`} {...rest} />
}
