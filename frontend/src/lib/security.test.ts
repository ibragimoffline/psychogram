import { afterEach, describe, expect, it, vi } from 'vitest'
import { can, canAccessPii } from './capabilities'
import { bootstrapEnabled } from './features'

afterEach(()=>vi.unstubAllEnvs())
describe('security policy',()=>{
 it('matches backend role capabilities without phantom actions',()=>{expect(can('auditor','result:export')).toBe(true);expect(can('auditor','response:write')).toBe(false);expect(can('operator','response:write')).toBe(true);expect(can('operator','result:read')).toBe(false);expect(can('researcher','result:calculate')).toBe(true)})
 it('requires both role and explicit PII permission',()=>{expect(canAccessPii({organization_id:'o',organization_name:'O',role:'operator',can_view_pii:true})).toBe(false);expect(canAccessPii({organization_id:'o',organization_name:'O',role:'researcher',can_view_pii:true})).toBe(true)})
 it('keeps bootstrap disabled unless explicitly enabled in dev',()=>{vi.stubEnv('VITE_ENABLE_BOOTSTRAP','false');expect(bootstrapEnabled()).toBe(false);vi.stubEnv('VITE_ENABLE_BOOTSTRAP','true');expect(bootstrapEnabled()).toBe(import.meta.env.DEV)})
})
