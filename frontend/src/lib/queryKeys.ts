export function tenantKey(organizationId: string | null | undefined, ...parts: readonly unknown[]) {
  return ['tenant', organizationId ?? 'none', ...parts] as const
}

