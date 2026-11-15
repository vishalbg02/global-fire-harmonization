/**
 * ISO 3166-1 alpha-3 code of a Natural Earth admin-0 feature, or null.
 * `ISO_A3` is "-99" for some countries (e.g. Norway, France); `ISO_A3_EH` fixes those.
 * Features without an ISO code (the six disputed or base-area polygons in the India point-of-view file, such as Bir Tawil)
 * return null; no code is invented for them.
 */
export function countryIso3(properties: Record<string, unknown> | null | undefined): string | null {
  const code = properties?.ISO_A3_EH
  return typeof code === 'string' && /^[A-Z]{3}$/.test(code) ? code : null
}

export function countryName(properties: Record<string, unknown> | null | undefined): string {
  const name = properties?.NAME ?? properties?.ADMIN
  return typeof name === 'string' ? name : 'Unknown country'
}
