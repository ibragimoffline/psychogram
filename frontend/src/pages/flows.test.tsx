import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { BrowserRouter } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import App from '../App'
import { AuthProvider } from '../context/AuthContext'
import { ParticipantDetail } from './ParticipantPages'

const me=(can_view_pii=false)=>({id:'u1',email:'a@example.com',full_name:'Aziza Karimova',is_platform_admin:false,memberships:[{organization_id:'org1',organization_name:'Meridian Lab',role:'owner',can_view_pii}]})
const research={id:'r1',tenant_id:'org1',name:'Diqqat tadqiqoti',purpose:'Professional tadqiqot',status:'active',methodology_version_id:'v1',pii_mode:'pseudonymous'}
const json=(value:unknown,status=200)=>Promise.resolve(new Response(JSON.stringify(value),{status,headers:{'Content-Type':'application/json'}}))

// findBy* resolves once the node exists; entry animations may still hold opacity 0 for a frame.
const visible=async(found:Promise<HTMLElement>)=>{const node=await found;await waitFor(()=>expect(node).toBeVisible());return node}

const retention=(id:string,days=365)=>({id,code:`days${days}`,retention_days:days,active:true,created_at:'2026-01-01'})
const version={id:'v1',methodology_id:'m1',methodology_code:'synth_demo',methodology_name:'Sintetik metodika',version_code:'1.0.0',lifecycle_status:'published',estimated_minutes:8,content_hash:'hash',snapshot:null,licence:{id:'l1',status:'verified',content_disclosure_level:'summary_only',allow_item_display:false,eligible:true,restrictions_i18n:{}},eligible:true,disclaimer_i18n:{}}
async function fillResearchForm(){await userEvent.type(await screen.findByLabelText('Tadqiqot nomi'),'Yangi research');await userEvent.type(screen.getByLabelText('Maqsad'),'Valid maqsad');await userEvent.selectOptions(await screen.findByLabelText('Metodika'),'v1');expect(screen.getByRole('option',{name:'Sintetik metodika · v1.0.0 · 8 daqiqa'})).toBeInTheDocument();await userEvent.type(screen.getByLabelText(/Rozilik hujjati yoki asosi/),'ethics/1');await userEvent.type(screen.getByLabelText('Rozilik shakli versiyasi'),'1.0')}

function start(path:string,fetcher:(input:RequestInfo|URL,init?:RequestInit)=>Promise<Response>){sessionStorage.setItem('psychogram_token','token');window.history.pushState({},'',path);vi.stubGlobal('fetch',vi.fn(fetcher));return render(<BrowserRouter><App/></BrowserRouter>)}

beforeEach(()=>{sessionStorage.clear()})
afterEach(()=>{vi.unstubAllGlobals();vi.unstubAllEnvs();sessionStorage.clear()})

describe('bootstrap production guard',()=>{
 it('hides the link and redirects direct access unless explicitly enabled',async()=>{vi.stubEnv('VITE_ENABLE_BOOTSTRAP','false');window.history.pushState({},'','/setup/bootstrap');render(<BrowserRouter><App/></BrowserRouter>);await visible(screen.findByRole('heading',{name:'Ish maydoniga kiring'}));expect(screen.queryByRole('link',{name:'Platformani sozlash'})).not.toBeInTheDocument();expect(window.location.pathname).toBe('/login')})
})

describe('pilot scope',()=>{
 it('hides self-registration unless explicitly enabled',async()=>{window.history.pushState({},'','/register');render(<BrowserRouter><App/></BrowserRouter>);await visible(screen.findByRole('heading',{name:'Ish maydoniga kiring'}));expect(window.location.pathname).toBe('/login');expect(screen.queryByRole('link',{name:'Tashkilot yaratish'})).not.toBeInTheDocument()})
 it('limits researcher navigation to researches and methodologies',async()=>{const researcher={...me(),memberships:[{...me().memberships[0],role:'researcher'}]};start('/researches',(input)=>String(input).includes('/auth/me')?json(researcher):json([]));const nav=await screen.findByRole('navigation',{name:'Asosiy navigatsiya'});await within(nav).findByRole('link',{name:'Tadqiqotlar'});expect(within(nav).getAllByRole('link').map(link=>link.getAttribute('aria-label'))).toEqual(['Tadqiqotlar','Metodikalar'])})
 it('hides CSV import inside a research unless explicitly enabled',async()=>{start('/researches/r1',(input)=>{const path=String(input);if(path.includes('/auth/me'))return json(me());if(path.endsWith('/researches'))return json([research]);return json({})});await screen.findByRole('link',{name:'Javoblar'});expect(screen.queryByRole('link',{name:'CSV import'})).not.toBeInTheDocument();expect(screen.queryByText('CSV orqali kiritish')).not.toBeInTheDocument()})
 it('does not route to CSV import unless explicitly enabled',async()=>{start('/researches/r1/import',(input)=>{const path=String(input);if(path.includes('/auth/me'))return json(me());if(path.endsWith('/researches'))return json([research]);return json({})});await waitFor(()=>expect(window.location.pathname).toBe('/researches'));expect(screen.queryByText(/CSV faylni tanlang/i)).not.toBeInTheDocument()})
})

describe('authenticated contracts',()=>{
 it('removes operator phantom create/result navigation actions',async()=>{const operator={...me(),memberships:[{...me().memberships[0],role:'operator'}]};start('/researches',(input)=>String(input).includes('/auth/me')?json(operator):json([]));await screen.findByRole('heading',{name:'Tadqiqotlar'});expect(screen.queryByRole('link',{name:'Yangi tadqiqot'})).not.toBeInTheDocument();expect(screen.queryByRole('link',{name:'Natijalar'})).not.toBeInTheDocument()})
 it('clears tenant-private reveal state and refetches with the selected tenant header',async()=>{
  const cancel=vi.spyOn(QueryClient.prototype,'cancelQueries')
  const profile={...me(),memberships:[...me().memberships,{organization_id:'org2',organization_name:'Yangi markaz',role:'researcher',can_view_pii:false}]}
  start('/researches',(input)=>{const path=String(input);if(path.includes('/auth/me'))return json(profile);if(path.includes('/researches'))return json([]);return json({})})
  sessionStorage.setItem('psychogram_pii_reveal','p1');const selector=await screen.findByLabelText('Faol tashkilot');await userEvent.selectOptions(selector,'org2');expect(cancel).toHaveBeenCalled();expect(sessionStorage.getItem('psychogram_pii_reveal')).toBeNull()
  await waitFor(()=>{const calls=(fetch as ReturnType<typeof vi.fn>).mock.calls.filter(([url])=>String(url).includes('/researches'));expect(calls.some(([,init])=>(init?.headers as Headers).get('X-Organization-ID')==='org2')).toBe(true)})
 })

 it('creates and starts a research with pilot defaults and navigates to its server id',async()=>{
  let posted:Record<string,unknown>|undefined;let activated=0
  start('/researches/new',async(input,init)=>{const path=String(input);if(path.includes('/auth/me'))return json(me());if(path.includes('/retention-policies'))return json([retention('ret1')]);if(path.includes('/methodology-versions/eligible'))return json([version]);if(path.endsWith('/researches')&&init?.method==='POST'){posted=JSON.parse(String(init.body));return json({...research,status:'ready'},201)}if(path.endsWith('/researches/r1/activate')){activated+=1;return json({...research,status:'active'})}if(path.endsWith('/researches'))return json([research]);return json({})})
  await fillResearchForm();expect(screen.queryByLabelText('Saqlash muddati')).not.toBeInTheDocument();expect(screen.getByText('365 kun')).toBeInTheDocument();await userEvent.click(screen.getByRole('button',{name:'Yaratish va boshlash'}))
  await waitFor(()=>expect(window.location.pathname).toBe('/researches/r1'));expect(activated).toBe(1);expect(posted).toEqual({name:'Yangi research',purpose:'Valid maqsad',methodology_version_id:'v1',pii_mode:'pseudonymous',consent_reference:'ethics/1',consent_version:'1.0',retention_policy_id:'ret1',use_type:'research',norm_selection:{}})
 })

 it('keeps the created research and offers to start it again when activation fails',async()=>{
  let creates=0;let activations=0
  start('/researches/new',async(input,init)=>{const path=String(input);if(path.includes('/auth/me'))return json(me());if(path.includes('/retention-policies'))return json([retention('ret1')]);if(path.includes('/methodology-versions/eligible'))return json([version]);if(path.endsWith('/researches')&&init?.method==='POST'){creates+=1;return json({...research,status:'ready'},201)}if(path.endsWith('/researches/r1/activate')){activations+=1;return activations===1?json({error:{code:'LICENCE_NOT_VALID',message:'Litsenziya yaroqsiz'}},409):json({...research,status:'active'})}if(path.endsWith('/researches'))return json([{...research,status:activations>1?'active':'ready'}]);return json({})})
  await fillResearchForm();await userEvent.click(screen.getByRole('button',{name:'Yaratish va boshlash'}))
  await waitFor(()=>expect(window.location.pathname).toBe('/researches/r1'));expect(creates).toBe(1);expect(await screen.findByText(/LICENCE_NOT_VALID/)).toBeInTheDocument();expect(screen.getByText('Boshlashga tayyor')).toBeInTheDocument()
  await userEvent.click(screen.getByRole('button',{name:'Tadqiqotni boshlash'}));await waitFor(()=>expect(activations).toBe(2));expect(creates).toBe(1);await waitFor(()=>expect(screen.queryByRole('button',{name:'Tadqiqotni boshlash'})).not.toBeInTheDocument())
 })

 it('asks for a retention period only when the organization has several',async()=>{
  let posted:Record<string,unknown>|undefined
  start('/researches/new',async(input,init)=>{const path=String(input);if(path.includes('/auth/me'))return json(me());if(path.includes('/retention-policies'))return json([retention('ret1'),retention('ret2',730)]);if(path.includes('/methodology-versions/eligible'))return json([version]);if(path.endsWith('/researches')&&init?.method==='POST'){posted=JSON.parse(String(init.body));return json({...research,status:'ready'},201)}if(path.endsWith('/activate'))return json({...research,status:'active'});if(path.endsWith('/researches'))return json([research]);return json({})})
  await fillResearchForm();await userEvent.selectOptions(screen.getByLabelText('Saqlash muddati'),'ret2');await userEvent.click(screen.getByRole('button',{name:'Yaratish va boshlash'}))
  await waitFor(()=>expect(posted?.retention_policy_id).toBe('ret2'))
 })

 it('uses server preview hash unchanged when confirming CSV',async()=>{
  let confirmBody:unknown
  vi.stubEnv('VITE_ENABLE_CSV_IMPORT','true')
start('/researches/r1/import',(input,init)=>{const path=String(input);if(path.includes('/auth/me'))return json(me());if(path.endsWith('/researches'))return json([research]);if(path.endsWith('/imports/preview'))return json({import_id:'imp1',status:'previewed',preview_hash:'server-hash-123',summary:{valid:1,invalid:0},errors:[{row_number:2,column_name:'item1',item_code:'item1',error_code:'TYPE_INVALID',severity:'error',message_key:'import.type_invalid',safe_params:{},rejected_value_preview:'***',suggested_action:'CSV qiymatini tuzating'}]},201);if(path.endsWith('/imports/imp1/confirm')){confirmBody=JSON.parse(String(init?.body));return json({import_id:'imp1',status:'confirmed',summary:{saved:1}})}return json({})})
const input=await screen.findByLabelText(/CSV faylni tanlang/i,{selector:'input'}).catch(()=>document.querySelector('input[type="file"]') as HTMLInputElement);const csv='external_code,item1\nP-1,2';const file=new File([csv],'answers.csv',{type:'text/csv'});Object.defineProperty(file,'arrayBuffer',{value:()=>Promise.resolve(new TextEncoder().encode(csv).buffer)});await userEvent.upload(input,file);await userEvent.click(await screen.findByRole('button',{name:'Tekshirish'}));await visible(screen.findByText('TYPE_INVALID'));expect(screen.getByText('CSV qiymatini tuzating')).toBeVisible();await userEvent.click(await screen.findByRole('button',{name:'Yaroqli qatorlarni saqlash'}));await waitFor(()=>expect(confirmBody).toEqual({preview_hash:'server-hash-123'}));await visible(screen.findByText(/saved: 1/))
 })

 it('keeps disclaimer visible, opens trace and requests only official JSON export',async()=>{
  const result={id:'res1',research_id:'r1',participant_id:'p1',response_revision_id:'rev1',status:'complete',disclaimer_i18n:{'uz-Latn':'Bu natija tibbiy tashxis emas.'},calculated_at:'2026-07-16T10:00:00Z',result_hash:'abc1234567890000',scales:[{scale_code:'total',validity_status:'valid',reason_codes:[],answered_count:1,missing_count:0,score_display:'5.00',unit_code:'point',norm_band_code:null,interpretation_snapshot_i18n:null,disclosure_level_applied:'derived_only'}],trace:[{step_name:'Aggregate',operation:'sum'}]}
  const create=vi.fn(()=> 'blob:url');Object.defineProperty(URL,'createObjectURL',{value:create,configurable:true});Object.defineProperty(URL,'revokeObjectURL',{value:vi.fn(),configurable:true});vi.spyOn(HTMLAnchorElement.prototype,'click').mockImplementation(()=>undefined)
start('/results/res1',(input)=>{const path=String(input);if(path.includes('/auth/me'))return json({...me(),memberships:[{...me().memberships[0],role:'researcher'}]});if(path.includes('/export?format=json'))return Promise.resolve(new Response('{}',{status:200}));if(path.endsWith('/results/res1'))return json(result);return json({})})
  expect((await screen.findAllByText(/Bu natija tibbiy tashxis emas/)).length).toBeGreaterThanOrEqual(1);await userEvent.click(screen.getByRole('button',{name:/Qanday hisoblandi/}));await visible(screen.findByText('Aggregate'));await userEvent.click(screen.getByRole('button',{name:'JSON'}));await waitFor(()=>expect(create).toHaveBeenCalled())
  const urls=(fetch as ReturnType<typeof vi.fn>).mock.calls.map(([url])=>String(url));expect(urls.some(url=>url.endsWith('/results/res1/export?format=json'))).toBe(true);expect(urls.some(url=>/format=(pdf|xlsx)/.test(url))).toBe(false)
 })

 it('shows results to auditors without export actions the server would reject',async()=>{
  const result={id:'res1',research_id:'r1',participant_id:'p1',response_revision_id:'rev1',status:'complete',disclaimer_i18n:{'uz-Latn':'Bu natija tibbiy tashxis emas.'},calculated_at:'2026-07-16T10:00:00Z',result_hash:'abc1234567890000',scales:[{scale_code:'total',validity_status:'valid',reason_codes:[],answered_count:1,missing_count:0,score_display:'5.00',unit_code:'point',norm_band_code:null,interpretation_snapshot_i18n:null,disclosure_level_applied:'derived_only'}],trace:[]}
  start('/results/res1',(input)=>{const path=String(input);if(path.includes('/auth/me'))return json({...me(),memberships:[{...me().memberships[0],role:'auditor'}]});if(path.endsWith('/results/res1'))return json(result);return json({})})
  expect(await screen.findByText('5.00',{exact:false})).toBeInTheDocument();expect(screen.queryByRole('button',{name:'JSON'})).not.toBeInTheDocument();expect(screen.queryByRole('button',{name:'CSV'})).not.toBeInTheDocument()
  expect((fetch as ReturnType<typeof vi.fn>).mock.calls.some(([url])=>String(url).includes('/export'))).toBe(false)
 })
})

describe('PII permission and deletion',()=>{
 function renderParticipant(_canView:boolean,handler:(input:RequestInfo|URL,init?:RequestInit)=>Promise<Response>){sessionStorage.setItem('psychogram_token','token');vi.stubGlobal('fetch',vi.fn(handler));const client=new QueryClient({defaultOptions:{queries:{retry:false}}});window.history.pushState({},'','/researches/r1/participants/p1');return render(<QueryClientProvider client={client}><AuthProvider><BrowserRouter><ParticipantDetail/></BrowserRouter></AuthProvider></QueryClientProvider>)}
 const participant={id:'p1',research_id:'r1',external_code:'P-014',processing_status:'active',created_at:'2026-07-16T10:00:00Z',current_consent_status:'granted',has_pii:true}
 it('never calls the PII endpoint without permission',async()=>{renderParticipant(false,(input)=>{const path=String(input);if(path.includes('/auth/me'))return json(me(false));if(path.endsWith('/p1'))return json(participant);if(path.endsWith('/consents'))return json({current:null,history:[]});return json({})});await visible(screen.findByText('PII ruxsati yo‘q'));expect((fetch as ReturnType<typeof vi.fn>).mock.calls.some(([url])=>String(url).endsWith('/pii'))).toBe(false)})
 it('remasks PII and removes plaintext from browser state',async()=>{renderParticipant(true,(input)=>{const path=String(input);if(path.includes('/auth/me'))return json(me(true));if(path.endsWith('/p1'))return json(participant);if(path.endsWith('/consents'))return json({current:null,history:[]});if(path.endsWith('/pii'))return json({participant_id:'p1',fields:{full_name:'Sir Ism'},algorithm:'AES-256-GCM',key_version:'1',updated_at:'2026-07-16'});return json({})});await userEvent.click(await screen.findByRole('button',{name:'Audit bilan ko‘rsatish'}));await visible(screen.findByDisplayValue('Sir Ism'));await userEvent.click(screen.getByRole('button',{name:'PIIni yashirish'}));expect(screen.queryByDisplayValue('Sir Ism')).not.toBeInTheDocument();await visible(screen.findByText(/brauzer holatidan tozalandi/))})
 it('requires a second destructive confirmation, deletes and removes plaintext',async()=>{let deleted=false;renderParticipant(true,(input,init)=>{const path=String(input);if(path.includes('/auth/me'))return json(me(true));if(path.endsWith('/p1'))return json(participant);if(path.endsWith('/consents'))return json({current:null,history:[]});if(path.endsWith('/pii')&&init?.method==='DELETE'){deleted=true;return Promise.resolve(new Response(null,{status:204}))}if(path.endsWith('/pii'))return json({participant_id:'p1',fields:{full_name:'Sir Ism'},algorithm:'AES-256-GCM',key_version:'1',updated_at:'2026-07-16'});return json({})});await userEvent.click(await screen.findByRole('button',{name:'Audit bilan ko‘rsatish'}));await visible(screen.findByDisplayValue('Sir Ism'));await userEvent.click(screen.getByRole('button',{name:'PII yozuvini o‘chirish'}));expect(deleted).toBe(false);await userEvent.click(screen.getByRole('button',{name:'Ha, PII yozuvini o‘chirish'}));await waitFor(()=>expect(deleted).toBe(true));expect(screen.queryByDisplayValue('Sir Ism')).not.toBeInTheDocument();await visible(screen.findByText(/plaintext holati tozalandi/))})
})
