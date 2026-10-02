import { useEffect } from 'react'
import { NavLink, Outlet, useLocation, useNavigate } from 'react-router-dom'
import { useQueryClient } from '@tanstack/react-query'
import { useAuth } from '../context/AuthContext'
import { can, type Capability } from '../lib/capabilities'
import type { Role } from '../types'
import { RemoteIcon } from './RemoteIcon'
import { Button } from './UI'

interface NavItem {to:string;label:string;icon:string;capability?:Capability}
const baseNav:NavItem[]=[
  {to:'/researches',label:'Tadqiqotlar',icon:'flask-conical'},
  {to:'/methodologies',label:'Metodikalar',icon:'notebook-tabs'},
  {to:'/team',label:'Jamoa',icon:'users-round',capability:'team:manage'},
  {to:'/retention',label:'Retention',icon:'archive',capability:'retention:manage'},
  {to:'/audit',label:'Audit',icon:'scroll-text',capability:'audit:read'},
]
const allowed=(item:NavItem,role:Role|undefined)=>!item.capability||can(role,item.capability)

export function AppShell(){
  const {me,membership,selectTenant,logout}=useAuth();const location=useLocation();const navigate=useNavigate();const queryClient=useQueryClient();const role=membership?.role
  const desktop=baseNav.filter(item=>allowed(item,role))
  const mobile=desktop.filter(item=>['/researches','/methodologies','/team','/audit'].includes(item.to)).slice(0,4)
  async function switchTenant(id:string){await queryClient.cancelQueries();queryClient.clear();selectTenant(id);navigate('/researches')}
  return <div className="app-shell">
    <a href="#main" className="skip-link">Asosiy kontentga o‘tish</a>
    <aside className="rail">
      <button className="wordmark" aria-label="Tadqiqotlar bosh sahifasi" onClick={()=>navigate('/researches')}><span className="registration-mark"/>PSYCHOGRAM</button>
      <label className="tenant-select"><span>Tashkilot</span><select aria-label="Faol tashkilot" value={membership?.organization_id??''} onChange={event=>void switchTenant(event.target.value)}>{me?.memberships.map(item=><option value={item.organization_id} key={item.organization_id}>{item.organization_name}</option>)}</select></label>
      <nav aria-label="Asosiy navigatsiya">{desktop.map(item=><NavLink to={item.to} key={item.to} aria-label={item.label} data-tooltip={item.label}><RemoteIcon name={item.icon} color="#C8D4CF"/><span>{item.label}</span></NavLink>)}{me?.is_platform_admin&&<NavLink to="/registry" aria-label="Registry" data-tooltip="Registry"><RemoteIcon name="badge-check" color="#C8D4CF"/><span>Registry</span></NavLink>}</nav>
      <div className="rail-user"><span>{me?.full_name}</span><small>{role??'Platform admin'}</small><Button aria-label="Chiqish" variant="quiet" onClick={()=>{queryClient.clear();logout()}}>Chiqish</Button></div>
    </aside>
<div className="workspace"><header className="topbar"><label className="tablet-tenant"><span className="visually-hidden">Tablet tenant selector</span><select aria-label="Faol tashkilot (tablet)" value={membership?.organization_id??''} onChange={event=>void switchTenant(event.target.value)}>{me?.memberships.map(item=><option value={item.organization_id} key={item.organization_id}>{item.organization_name}</option>)}</select></label><span>{location.pathname.split('/').filter(Boolean).map(x=>x.length>24?`${x.slice(0,8)}…`:x).join(' / ')||'Ish maydoni'}</span><div><StatusContext/></div></header><RouteFocus/><main id="main" tabIndex={-1} key={membership?.organization_id}><Outlet/></main></div>
    <nav className="mobile-nav" aria-label="Mobil navigatsiya">{mobile.map(item=><NavLink to={item.to} key={item.to}><RemoteIcon name={item.icon} color="#C8D4CF"/><span>{item.label}</span></NavLink>)}</nav>
  </div>
}

function RouteFocus(){const location=useLocation();useEffect(()=>{const timer=window.setTimeout(()=>{const heading=document.querySelector<HTMLElement>('main#main h1');if(heading){heading.tabIndex=-1;heading.focus();document.title=`${heading.textContent??'Psychogram'} — Psychogram`}},0);return()=>window.clearTimeout(timer)},[location.pathname]);return null}
function StatusContext(){const {membership}=useAuth();return <span className="role-context"><RemoteIcon name="shield" size={16}/>{membership?.role}{membership?.can_view_pii?' · PII ruxsati':''}</span>}
