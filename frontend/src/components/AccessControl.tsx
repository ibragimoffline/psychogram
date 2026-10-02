import type { ReactNode } from 'react'
import { can, type Capability } from '../lib/capabilities'
import { useAuth } from '../context/AuthContext'
import { Notice, Page } from './UI'

export function RequireCapability({capability,children}:{capability:Capability;children:ReactNode}){
  const {membership}=useAuth()
  if(can(membership?.role,capability))return children
  return <Page title="Ruxsat yo‘q"><Notice tone="danger" title="Amal sizning rolingiz uchun yopiq">Server ruxsatlari authoritative. Ruxsatli ish maydoniga qayting.</Notice></Page>
}
