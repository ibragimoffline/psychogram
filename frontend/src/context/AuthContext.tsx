import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from 'react'
import { api } from '../lib/api'
import type { Me, Membership } from '../types'

interface AuthValue {token:string|null;me:Me|null;membership:Membership|null;loading:boolean;setSession:(token:string)=>Promise<void>;selectTenant:(id:string)=>void;logout:()=>void}
const AuthContext=createContext<AuthValue|null>(null)

export function AuthProvider({children}:{children:ReactNode}){
  const [token,setToken]=useState<string|null>(()=>sessionStorage.getItem('psychogram_token'))
  const [me,setMe]=useState<Me|null>(null); const [membership,setMembership]=useState<Membership|null>(null); const [loading,setLoading]=useState(Boolean(token))
  const hydrate=useCallback(async(value:string)=>{
    const profile=await api<Me>('/api/v1/auth/me',{token:value});setMe(profile)
    const saved=sessionStorage.getItem('psychogram_tenant');setMembership(profile.memberships.find(m=>m.organization_id===saved)??profile.memberships[0]??null)
  },[])
  useEffect(()=>{if(token){hydrate(token).catch(()=>{sessionStorage.clear();setToken(null)}).finally(()=>setLoading(false))}},[token,hydrate])
  const setSession=useCallback(async(value:string)=>{sessionStorage.setItem('psychogram_token',value);setToken(value);setLoading(true);try{await hydrate(value)}finally{setLoading(false)}},[hydrate])
  const selectTenant=useCallback((id:string)=>{const next=me?.memberships.find(m=>m.organization_id===id)??null;setMembership(next);sessionStorage.setItem('psychogram_tenant',id);sessionStorage.removeItem('psychogram_pii_reveal')},[me])
  const logout=useCallback(()=>{sessionStorage.removeItem('psychogram_token');sessionStorage.removeItem('psychogram_tenant');sessionStorage.removeItem('psychogram_pii_reveal');setToken(null);setMe(null);setMembership(null)},[])
  const value=useMemo(()=>({token,me,membership,loading,setSession,selectTenant,logout}),[token,me,membership,loading,setSession,selectTenant,logout])
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}
export function useAuth(){const value=useContext(AuthContext);if(!value)throw new Error('AuthProvider missing');return value}
export function useApi(){const {token,membership}=useAuth();return <T,>(path:string,options:Parameters<typeof api<T>>[1]={})=>api<T>(path,{...options,token,organizationId:membership?.organization_id})}
