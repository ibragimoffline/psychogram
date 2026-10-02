import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from 'react'
import { api, ApiError } from '../lib/api'
import { queryClient } from '../lib/queryClient'
import type { Me, Membership } from '../types'

interface AuthValue {token:string|null;me:Me|null;membership:Membership|null;loading:boolean;setSession:(token:string)=>Promise<void>;selectTenant:(id:string)=>void;logout:()=>void;expireSession:()=>void}

export const SESSION_EXPIRED_KEY='psychogram_session_expired'
const AuthContext=createContext<AuthValue|null>(null)

export function AuthProvider({children}:{children:ReactNode}){
  const [token,setToken]=useState<string|null>(()=>sessionStorage.getItem('psychogram_token'))
  const [me,setMe]=useState<Me|null>(null); const [membership,setMembership]=useState<Membership|null>(null); const [loading,setLoading]=useState(Boolean(token))
  const hydrate=useCallback(async(value:string)=>{
    const profile=await api<Me>('/api/v1/auth/me',{token:value});setMe(profile)
    const saved=sessionStorage.getItem('psychogram_tenant');setMembership(profile.memberships.find(m=>m.organization_id===saved)??profile.memberships[0]??null)
  },[])
  useEffect(()=>{if(token){hydrate(token).catch(error=>{sessionStorage.clear();if(error instanceof ApiError&&error.status===401)sessionStorage.setItem(SESSION_EXPIRED_KEY,'1');setToken(null)}).finally(()=>setLoading(false))}},[token,hydrate])
  const setSession=useCallback(async(value:string)=>{sessionStorage.setItem('psychogram_token',value);setToken(value);setLoading(true);try{await hydrate(value)}finally{setLoading(false)}},[hydrate])
  const selectTenant=useCallback((id:string)=>{const next=me?.memberships.find(m=>m.organization_id===id)??null;setMembership(next);sessionStorage.setItem('psychogram_tenant',id);sessionStorage.removeItem('psychogram_pii_reveal')},[me])
  const logout=useCallback(()=>{sessionStorage.removeItem('psychogram_token');sessionStorage.removeItem('psychogram_tenant');sessionStorage.removeItem('psychogram_pii_reveal');setToken(null);setMe(null);setMembership(null)},[])
  const expireSession=useCallback(()=>{queryClient.clear();logout();sessionStorage.setItem(SESSION_EXPIRED_KEY,'1')},[logout])
  const value=useMemo(()=>({token,me,membership,loading,setSession,selectTenant,logout,expireSession}),[token,me,membership,loading,setSession,selectTenant,logout,expireSession])
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}
export function useAuth(){const value=useContext(AuthContext);if(!value)throw new Error('AuthProvider missing');return value}
// A 401 on an authenticated call means the token expired or was revoked: end the session so the user signs in again.
export function useApi(){const {token,membership,expireSession}=useAuth();return async <T,>(path:string,options:Parameters<typeof api<T>>[1]={})=>{try{return await api<T>(path,{...options,token,organizationId:membership?.organization_id})}catch(error){if(token&&error instanceof ApiError&&error.status===401)expireSession();throw error}}}
