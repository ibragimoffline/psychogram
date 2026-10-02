import { QueryClientProvider } from '@tanstack/react-query'
import { Navigate, Outlet, Route, Routes } from 'react-router-dom'
import { RequireCapability } from './components/AccessControl'
import { AppShell } from './components/AppShell'
import { ErrorBoundary } from './components/ErrorBoundary'
import { Loading } from './components/UI'
import { AuthProvider, useAuth } from './context/AuthContext'
import { bootstrapEnabled, csvImportEnabled, registrationEnabled } from './lib/features'
import { queryClient } from './lib/queryClient'
import { AuditPage, MethodologiesPage, MethodologyDetail, RegistryPage, RetentionPage, TeamPage } from './pages/AdminPages'
import { BootstrapPage, LoginPage, RegisterPage } from './pages/AuthPages'
import { ParticipantDetail, ParticipantsPage } from './pages/ParticipantPages'
import { ResponseForm } from './pages/ResponseForm'
import { ResponseDetailPage, ResponsesPage } from './pages/ResponsePages'
import { ImportPage, ResultDetail, ResultsPage } from './pages/ResultImportPages'
import { ResearchCreate, ResearchLayout, ResearchList, ResearchOverview } from './pages/ResearchPages'

const gate=(capability:Parameters<typeof RequireCapability>[0]['capability'],element:React.ReactNode)=><RequireCapability capability={capability}>{element}</RequireCapability>

export default function App(){return <ErrorBoundary><QueryClientProvider client={queryClient}><AuthProvider><Routes>
  <Route path="/login" element={<LoginPage/>}/><Route path="/register" element={registrationEnabled()?<RegisterPage/>:<Navigate to="/login" replace/>}/><Route path="/setup/bootstrap" element={bootstrapEnabled()?<BootstrapPage/>:<Navigate to="/login" replace/>}/>
  <Route element={<Protected/>}><Route path="/" element={<AppShell/>}>
    <Route index element={<Navigate to="/researches" replace/>}/><Route path="researches" element={<ResearchList/>}/><Route path="researches/new" element={gate('research:create',<ResearchCreate/>)}/>
    <Route path="researches/:researchId" element={<ResearchLayout/>}><Route index element={<ResearchOverview/>}/><Route path="participants" element={<ParticipantsPage/>}/><Route path="participants/:participantId" element={<ParticipantDetail/>}/><Route path="responses" element={<ResponsesPage/>}/><Route path="responses/:responseId" element={gate('response:write',<ResponseForm/>)}/>{csvImportEnabled()&&<Route path="import" element={gate('response:write',<ImportPage/>)}/>}<Route path="results" element={gate('result:read',<ResultsPage/>)}/></Route>
    <Route path="responses/:responseId" element={<ResponseDetailPage/>}/><Route path="results" element={gate('result:read',<ResultsPage/>)}/><Route path="results/:resultId" element={gate('result:read',<ResultDetail/>)}/><Route path="methodologies" element={<MethodologiesPage/>}/><Route path="methodologies/:methodologyId" element={<MethodologyDetail/>}/><Route path="team" element={gate('team:manage',<TeamPage/>)}/><Route path="retention" element={gate('retention:manage',<RetentionPage/>)}/><Route path="audit" element={gate('audit:read',<AuditPage/>)}/><Route path="registry" element={<RegistryPage/>}/><Route path="*" element={<Navigate to="/researches" replace/>}/>
  </Route></Route>
</Routes></AuthProvider></QueryClientProvider></ErrorBoundary>}

function Protected(){const {token,loading}=useAuth();if(loading)return <Loading label="Sessiya tekshirilmoqda"/>;return token?<Outlet/>:<Navigate to="/login" replace/>}
