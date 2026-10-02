export function bootstrapEnabled(): boolean {
  return import.meta.env.DEV && import.meta.env.VITE_ENABLE_BOOTSTRAP === 'true'
}

export function maxCsvBytes(): number {
  const configured = Number(import.meta.env.VITE_MAX_CSV_BYTES)
  return Number.isSafeInteger(configured) && configured > 0 ? configured : 1_000_000
}

