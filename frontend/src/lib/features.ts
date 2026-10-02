export function bootstrapEnabled(): boolean {
  return import.meta.env.DEV && import.meta.env.VITE_ENABLE_BOOTSTRAP === 'true'
}

// Pilot accounts are prepared by a platform administrator; the backend has its own flag.
export function registrationEnabled(): boolean {
  return import.meta.env.VITE_ENABLE_REGISTRATION === 'true'
}

// CSV import is outside the first pilot release; the backend has its own flag.
export function csvImportEnabled(): boolean {
  return import.meta.env.VITE_ENABLE_CSV_IMPORT === 'true'
}

export function maxCsvBytes(): number {
  const configured = Number(import.meta.env.VITE_MAX_CSV_BYTES)
  return Number.isSafeInteger(configured) && configured > 0 ? configured : 1_000_000
}

