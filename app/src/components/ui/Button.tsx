import type { ButtonHTMLAttributes } from 'react'

export type ButtonVariant = 'primary' | 'secondary' | 'ghost'

interface Props extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant
}

/** The one button: primary (filled navy), secondary (outlined) and ghost (on the navy header). */
export function Button({ variant = 'secondary', className, type = 'button', ...rest }: Props) {
  return <button type={type} className={`btn btn-${variant}${className === undefined ? '' : ` ${className}`}`} {...rest} />
}
