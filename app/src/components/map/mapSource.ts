import { useEffect, useState } from 'react'

/** "MODIS/Aqua MYD14 V061" gives "MYD14"; "VIIRS S-NPP VNP14IMGT NRT" gives "VNP14IMGT"; null if no product code is found. */
export function productCode(name: string): string | null {
  return name.split(/\s+/).find((t) => /^[A-Z]{2,3}1?14[A-Z]*$/.test(t)) ?? null
}

const codes = (list: readonly { name: string }[]) =>
  list.map((d) => productCode(d.name)).filter((c): c is string => c !== null)

export interface FirmsProducts {
  standard: string[]
  nearRealTime: string[]
}

/** The product codes of the standard (SP) and the near-real-time (NRT) FIRMS products, from a dataset list like the methods page's. */
export function firmsProducts(datasets: {
  standard: readonly { name: string }[]
  nearRealTime: readonly { name: string }[]
}): FirmsProducts {
  return { standard: codes(datasets.standard), nearRealTime: codes(datasets.nearRealTime) }
}

/**
 * The products from the methods page's dataset list (DATASET_DOIS). That file is large and the
 * methods page loads it anyway, so it is loaded after the first paint and keeps the first load small.
 */
export function useFirmsProducts(): FirmsProducts | null {
  const [products, setProducts] = useState<FirmsProducts | null>(null)
  useEffect(() => {
    let live = true
    void import('../../content/methods.ts').then((m) => {
      if (live) setProducts(firmsProducts(m.DATASET_DOIS))
    })
    return () => {
      live = false
    }
  }, [])
  return products
}
