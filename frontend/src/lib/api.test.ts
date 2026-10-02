import { afterEach, describe, expect, it, vi } from 'vitest'
import { api, ApiError, download } from './api'

afterEach(()=>vi.unstubAllGlobals())
describe('api client',()=>{
 it('adds bearer and tenant headers',async()=>{const fetch=vi.fn().mockResolvedValue(new Response(JSON.stringify({ok:true}),{status:200,headers:{'Content-Type':'application/json'}}));vi.stubGlobal('fetch',fetch);await api('/api/v1/researches',{token:'token',organizationId:'org'});const init=fetch.mock.calls[0][1] as RequestInit;const headers=init.headers as Headers;expect(headers.get('Authorization')).toBe('Bearer token');expect(headers.get('X-Organization-ID')).toBe('org')})
 it('maps stable domain errors safely',async()=>{vi.stubGlobal('fetch',vi.fn().mockResolvedValue(new Response(JSON.stringify({error:{code:'CONSENT_REQUIRED',message:'blocked'}}),{status:409,headers:{'Content-Type':'application/json'}})));await expect(api('/api/v1/x')).rejects.toMatchObject({status:409,code:'CONSENT_REQUIRED'} satisfies Partial<ApiError>)})
 it('does not attach tenant header when omitted',async()=>{const fetch=vi.fn().mockResolvedValue(new Response(JSON.stringify({}),{status:200,headers:{'Content-Type':'application/json'}}));vi.stubGlobal('fetch',fetch);await api('/api/v1/auth/me',{token:'a'});const headers=fetch.mock.calls[0][1].headers as Headers;expect(headers.has('X-Organization-ID')).toBe(false)})
 it('keeps stable domain errors for failed downloads',async()=>{vi.stubGlobal('fetch',vi.fn().mockResolvedValue(new Response(JSON.stringify({error:{code:'LICENCE_REVOKED',message:'Export bloklangan',details:{gate:'licence'}}}),{status:409,headers:{'Content-Type':'application/json'}})));await expect(download('/export','token','org','x.json')).rejects.toMatchObject({status:409,code:'LICENCE_REVOKED',details:{gate:'licence'}} satisfies Partial<ApiError>)})
})
