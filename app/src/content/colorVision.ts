/**
 * Colour-vision tools: dichromacy simulation, colour difference and WCAG contrast.
 *
 * Simulation uses the severity 1.0 matrices of Machado, Oliveira and Fernandes (2009), "A
 * Physiologically-based Model for Simulation of Color Vision Deficiency", IEEE TVCG 15(6).
 * They act on linear RGB: sRGB is decoded to linear light, multiplied by the matrix, encoded
 * back to sRGB and clamped to the gamut.
 *
 * This module has no dependency and does not touch the app; it exists for tests and for
 * taking screenshots under simulation (see `simulationFilterValues`).
 */

export type Rgb = readonly [number, number, number]
export type Lab = readonly [number, number, number]
export type CvdType = 'protanopia' | 'deuteranopia' | 'tritanopia'

export const CVD_TYPES: readonly CvdType[] = ['protanopia', 'deuteranopia', 'tritanopia']

type Matrix3 = readonly [
  readonly [number, number, number],
  readonly [number, number, number],
  readonly [number, number, number],
]

/** Machado, Oliveira and Fernandes (2009), severity 1.0, applied to linear RGB. */
export const MACHADO_MATRICES: Record<CvdType, Matrix3> = {
  protanopia: [
    [0.152286, 1.052583, -0.204868],
    [0.114503, 0.786281, 0.099216],
    [-0.003882, -0.048116, 1.051998],
  ],
  deuteranopia: [
    [0.367322, 0.860646, -0.227968],
    [0.280085, 0.672501, 0.047413],
    [-0.01182, 0.04294, 0.968881],
  ],
  tritanopia: [
    [1.255528, -0.076749, -0.178779],
    [-0.078411, 0.930809, 0.147602],
    [0.004733, 0.691367, 0.3039],
  ],
}

// ---------------------------------------------------------------------------------------------
// Parsing

/** Parse `#rgb`, `#rrggbb`, or `rgb(r, g, b)` / `rgba(r, g, b, a)` (alpha ignored) into 0-255. */
export function parseColor(input: string): Rgb {
  const s = input.trim().toLowerCase()
  const hex = /^#([0-9a-f]{3}|[0-9a-f]{6})$/.exec(s)
  if (hex !== null) {
    const h = hex[1].length === 3 ? [...hex[1]].map((c) => c + c).join('') : hex[1]
    return [parseInt(h.slice(0, 2), 16), parseInt(h.slice(2, 4), 16), parseInt(h.slice(4, 6), 16)]
  }
  const fn = /^rgba?\(\s*(\d+(?:\.\d+)?)\s*,\s*(\d+(?:\.\d+)?)\s*,\s*(\d+(?:\.\d+)?)\s*(?:,\s*[\d.]+\s*)?\)$/.exec(s)
  if (fn !== null) {
    const v = [Number(fn[1]), Number(fn[2]), Number(fn[3])]
    if (v.every((c) => c >= 0 && c <= 255)) return [v[0], v[1], v[2]]
  }
  throw new Error(`Cannot parse colour: ${input}`)
}

export const parseHex = parseColor

export function rgbToHex(rgb: Rgb): string {
  return `#${rgb.map((c) => Math.round(Math.min(Math.max(c, 0), 255)).toString(16).padStart(2, '0')).join('')}`
}

// ---------------------------------------------------------------------------------------------
// sRGB, linear RGB, luminance

export function srgbToLinear(c: number): number {
  const s = c / 255
  return s <= 0.04045 ? s / 12.92 : ((s + 0.055) / 1.055) ** 2.4
}

/** Linear light (0 to 1) to sRGB (0 to 255), not rounded. */
export function linearToSrgb(l: number): number {
  const v = l <= 0.0031308 ? l * 12.92 : 1.055 * l ** (1 / 2.4) - 0.055
  return v * 255
}

/** WCAG 2.x relative luminance (0 to 1). */
export function relativeLuminance(rgb: Rgb): number {
  return 0.2126 * srgbToLinear(rgb[0]) + 0.7152 * srgbToLinear(rgb[1]) + 0.0722 * srgbToLinear(rgb[2])
}

/** WCAG 2.x contrast ratio (1 to 21). */
export function contrastRatio(a: Rgb, b: Rgb): number {
  const la = relativeLuminance(a)
  const lb = relativeLuminance(b)
  return (Math.max(la, lb) + 0.05) / (Math.min(la, lb) + 0.05)
}

// ---------------------------------------------------------------------------------------------
// Simulation

/** Simulate a dichromat's view of an sRGB colour. Result is clamped to 0-255 and not rounded. */
export function simulate(rgb: Rgb, type: CvdType): [number, number, number] {
  const lin = [srgbToLinear(rgb[0]), srgbToLinear(rgb[1]), srgbToLinear(rgb[2])]
  const m = MACHADO_MATRICES[type]
  const out = m.map((row) => row[0] * lin[0] + row[1] * lin[1] + row[2] * lin[2])
  const enc = out.map((v) => Math.min(Math.max(linearToSrgb(Math.min(Math.max(v, 0), 1)), 0), 255))
  return [enc[0], enc[1], enc[2]]
}

/**
 * Values for an SVG `feColorMatrix type="matrix"` (4x5, row-major, as a space-separated string)
 * so screenshots can be taken under simulation.
 *
 * These are the same Machado 3x3 matrices, with the alpha row left alone. They are exact only if
 * the filter works in linear light, which is the SVG default (`color-interpolation-filters`
 * `linearRGB`): the browser then does the sRGB to linear, matrix, back to sRGB and clamp steps.
 * With `color-interpolation-filters="sRGB"` the matrix is applied directly to gamma-encoded
 * values, which is only an approximation of `simulate` (colours shift by a few delta E).
 */
export function simulationFilterValues(type: CvdType): string {
  const m = MACHADO_MATRICES[type]
  const rows = m.map((r) => `${r[0]} ${r[1]} ${r[2]} 0 0`)
  rows.push('0 0 0 1 0')
  return rows.join(' ')
}

// ---------------------------------------------------------------------------------------------
// CIE Lab (D65) and CIEDE2000

const WHITE_D65 = [0.95047, 1, 1.08883] as const

/** CIE L*a*b* (D65 white point) from sRGB 0-255; accepts non-integer channels. */
export function rgbToLab(rgb: Rgb): Lab {
  const r = srgbToLinear(rgb[0])
  const g = srgbToLinear(rgb[1])
  const b = srgbToLinear(rgb[2])
  const x = 0.4124564 * r + 0.3575761 * g + 0.1804375 * b
  const y = 0.2126729 * r + 0.7151522 * g + 0.072175 * b
  const z = 0.0193339 * r + 0.119192 * g + 0.9503041 * b
  const f = (t: number) => (t > 216 / 24389 ? Math.cbrt(t) : ((24389 / 27) * t + 16) / 116)
  const fx = f(x / WHITE_D65[0])
  const fy = f(y / WHITE_D65[1])
  const fz = f(z / WHITE_D65[2])
  return [116 * fy - 16, 500 * (fx - fy), 200 * (fy - fz)]
}

const rad = (d: number) => (d * Math.PI) / 180
const deg = (r: number) => (r * 180) / Math.PI

/** CIEDE2000 colour difference between two Lab colours (kL = kC = kH = 1). */
export function deltaE2000(lab1: Lab, lab2: Lab): number {
  const [L1, a1, b1] = lab1
  const [L2, a2, b2] = lab2
  const C1 = Math.hypot(a1, b1)
  const C2 = Math.hypot(a2, b2)
  const Cbar = (C1 + C2) / 2
  const G = 0.5 * (1 - Math.sqrt(Cbar ** 7 / (Cbar ** 7 + 25 ** 7)))
  const a1p = (1 + G) * a1
  const a2p = (1 + G) * a2
  const C1p = Math.hypot(a1p, b1)
  const C2p = Math.hypot(a2p, b2)
  const hue = (b: number, ap: number) => {
    if (b === 0 && ap === 0) return 0
    const h = deg(Math.atan2(b, ap))
    return h < 0 ? h + 360 : h
  }
  const h1p = hue(b1, a1p)
  const h2p = hue(b2, a2p)

  const dLp = L2 - L1
  const dCp = C2p - C1p
  let dhp = 0
  if (C1p * C2p !== 0) {
    dhp = h2p - h1p
    if (dhp > 180) dhp -= 360
    else if (dhp < -180) dhp += 360
  }
  const dHp = 2 * Math.sqrt(C1p * C2p) * Math.sin(rad(dhp / 2))

  const Lbarp = (L1 + L2) / 2
  const Cbarp = (C1p + C2p) / 2
  let hbarp: number
  if (C1p * C2p === 0) hbarp = h1p + h2p
  else if (Math.abs(h1p - h2p) <= 180) hbarp = (h1p + h2p) / 2
  else if (h1p + h2p < 360) hbarp = (h1p + h2p + 360) / 2
  else hbarp = (h1p + h2p - 360) / 2

  const T =
    1 -
    0.17 * Math.cos(rad(hbarp - 30)) +
    0.24 * Math.cos(rad(2 * hbarp)) +
    0.32 * Math.cos(rad(3 * hbarp + 6)) -
    0.2 * Math.cos(rad(4 * hbarp - 63))
  const dTheta = 30 * Math.exp(-(((hbarp - 275) / 25) ** 2))
  const Rc = 2 * Math.sqrt(Cbarp ** 7 / (Cbarp ** 7 + 25 ** 7))
  const Sl = 1 + (0.015 * (Lbarp - 50) ** 2) / Math.sqrt(20 + (Lbarp - 50) ** 2)
  const Sc = 1 + 0.045 * Cbarp
  const Sh = 1 + 0.015 * Cbarp * T
  const Rt = -Math.sin(rad(2 * dTheta)) * Rc

  return Math.sqrt(
    (dLp / Sl) ** 2 + (dCp / Sc) ** 2 + (dHp / Sh) ** 2 + Rt * (dCp / Sc) * (dHp / Sh),
  )
}

/** CIEDE2000 between two sRGB colours, each optionally seen through a dichromacy simulation. */
export function deltaE2000Rgb(a: Rgb, b: Rgb, type?: CvdType): number {
  const pa = type === undefined ? a : simulate(a, type)
  const pb = type === undefined ? b : simulate(b, type)
  return deltaE2000(rgbToLab(pa), rgbToLab(pb))
}
