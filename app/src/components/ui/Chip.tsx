import type { ButtonHTMLAttributes } from 'react'

interface Props extends ButtonHTMLAttributes<HTMLButtonElement> {
  selected?: boolean
}

/** A small toggle button (the featured stories). `aria-pressed` carries the state, not colour alone. */
export function Chip({ selected = false, className, type = 'button', ...rest }: Props) {
  return (
    <button
      type={type}
      className={`chip${selected ? ' chip-on' : ''}${className === undefined ? '' : ` ${className}`}`}
      aria-pressed={selected}
      {...rest}
    />
  )
}
