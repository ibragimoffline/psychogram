import type { Membership, Role } from '../types'

export type Capability =
  | 'research:create'
  | 'research:activate'
  | 'research:close'
  | 'participant:write'
  | 'response:write'
  | 'result:calculate'
  | 'result:read'
  | 'result:export'
  | 'team:manage'
  | 'retention:manage'
  | 'audit:read'

const policy: Record<Capability, readonly Role[]> = {
  'research:create': ['owner', 'admin', 'researcher'],
  'research:activate': ['owner', 'admin', 'researcher'],
  'research:close': ['owner', 'admin', 'researcher'],
  'participant:write': ['owner', 'admin', 'researcher', 'operator'],
  'response:write': ['owner', 'admin', 'researcher', 'operator'],
  'result:calculate': ['owner', 'admin', 'researcher'],
  'result:read': ['owner', 'admin', 'researcher', 'auditor'],
  'result:export': ['owner', 'admin', 'researcher'],
  'team:manage': ['owner', 'admin'],
  'retention:manage': ['owner', 'admin'],
  'audit:read': ['owner', 'admin', 'auditor'],
}

export function can(role: Role | null | undefined, capability: Capability): boolean {
  return Boolean(role && policy[capability].includes(role))
}

export function canAccessPii(membership: Membership | null | undefined): boolean {
  return Boolean(
    membership?.can_view_pii &&
      membership.role &&
      ['owner', 'admin', 'researcher'].includes(membership.role),
  )
}

