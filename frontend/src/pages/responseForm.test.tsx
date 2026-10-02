import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { BrowserRouter } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import App from '../App'

const me={id:'u1',email:'r@example.com',full_name:'Researcher',is_platform_admin:false,memberships:[{organization_id:'org1',organization_name:'Lab',role:'researcher',can_view_pii:false}]}
const research={id:'r1',tenant_id:'org1',name:'Pilot',purpose:'Test',status:'active',methodology_version_id:'v1',pii_mode:'pseudonymous',consent_reference:'ETIKA-2026',consent_version:'1.0'}
const version={id:'v1',methodology_id:'m1',methodology_code:'demo',methodology_name:'Demo metodika',version_code:'1.0.0',lifecycle_status:'published',estimated_minutes:5,content_hash:'h',eligible:true,disclaimer_i18n:{},licence:{id:'l1',status:'verified',content_disclosure_level:'full',allow_item_display:true,eligible:true,restrictions_i18n:{}},snapshot:{items:[{item_code:'q1',item_type:'integer',required:true,prompt_i18n:{'uz-Latn':'Necha marta?'}},{item_code:'q2',item_type:'single_choice',required:true,prompt_i18n:{'uz-Latn':'Kayfiyat'},options:[{option_code:'a',label_i18n:{'uz-Latn':'Yaxshi'}},{option_code:'b',label_i18n:{'uz-Latn':'Yomon'}}]}]}}
const json=(value:unknown,status=200)=>Promise.resolve(new Response(JSON.stringify(value),{status,headers:{'Content-Type':'application/json'}}))
const error=(code:string,status=409)=>json({error:{code,message:code}},status)

interface Call {method:string;path:string;body?:Record<string,unknown>}
// A small stateful stand-in for the backend: enough to exercise create, reuse, validate and score.
function fakeServer(options:{validate?:(answers:Record<string,unknown>)=>{item_code:string;error_code:string}[];failFirstCalculation?:boolean;existing?:boolean}={}){
 const calls:Call[]=[];const state={participant:null as null|{id:string;external_code:string;current_consent_status:string|null},response:null as null|{id:string;lock_version:number;revision:{id:string;revision_number:number;status:string;answers:Record<string,unknown>;validation_issues:unknown[]}},calculations:0}
 if(options.existing){state.participant={id:'p1',external_code:'P001',current_consent_status:'granted'};state.response={id:'resp1',lock_version:2,revision:{id:'rev2',revision_number:2,status:'validated',answers:{q1:3,q2:'a'},validation_issues:[]}}}
 const detail=()=>{const r=state.response!;return {id:r.id,research_id:'r1',participant_id:'p1',participant_external_code:'P001',attempt_key:'initial',status:r.revision.status,lock_version:r.lock_version,current_revision_id:r.revision.id,current_revision_number:r.revision.revision_number,current_revision_status:r.revision.status,created_at:'2026-10-02T10:00:00Z',result_status:'not_calculated',current_result_id:null,methodology_version_id:'v1',current_revision:{...r.revision,response_id:r.id,answer_payload_hash:'sha256:x',validation_summary:{},is_current:true,correction_reason:null,created_at:'2026-10-02T10:00:00Z',source_type:'manual'}}}
 const handler=async(input:RequestInfo|URL,init?:RequestInit)=>{
  const url=new URL(String(input),'http://localhost');const path=url.pathname;const method=init?.method??'GET';const body=init?.body?JSON.parse(String(init.body)):undefined;calls.push({method,path:path+url.search,body})
  if(path==='/api/v1/auth/me')return json(me)
  if(path==='/api/v1/researches')return json([research])
  if(path==='/api/v1/methodology-versions/v1')return json(version)
  if(path==='/api/v1/researches/r1/participants'&&method==='POST'){if(state.participant)return error('PARTICIPANT_CODE_EXISTS');state.participant={id:'p1',external_code:body.external_code,current_consent_status:null};return json({...state.participant,research_id:'r1',processing_status:'active'},201)}
  if(path==='/api/v1/researches/r1/participants')return json({items:state.participant?[{...state.participant,research_id:'r1',processing_status:'active',created_at:'',has_pii:false}]:[],total:state.participant?1:0,offset:0,limit:100})
  if(path==='/api/v1/researches/r1/participants/p1')return json({...state.participant,research_id:'r1',processing_status:'active',created_at:'',has_pii:false})
  if(path==='/api/v1/participants/p1/consents'){state.participant!.current_consent_status='granted';return json({id:'c1'},201)}
  if(path==='/api/v1/researches/r1/responses'&&method==='POST'){if(state.response)return error('RESPONSE_ATTEMPT_EXISTS');state.response={id:'resp1',lock_version:1,revision:{id:'rev1',revision_number:1,status:'draft',answers:body.answers,validation_issues:[]}};return json({id:'resp1',lock_version:1,current_revision_id:'rev1',status:'draft'},201)}
  if(path==='/api/v1/researches/r1/responses')return json({items:state.response?[detail()]:[],total:state.response?1:0,offset:0,limit:50})
  if(path==='/api/v1/responses/resp1/revisions'&&method==='POST'){const r=state.response!;if(body.expected_lock_version!==r.lock_version)return error('REVISION_CONFLICT');if(r.revision.status==='validated'&&!body.correction_reason)return error('CORRECTION_REASON_REQUIRED',400);const n=r.revision.revision_number+1;r.revision={id:`rev${n}`,revision_number:n,status:'draft',answers:body.answers,validation_issues:[]};r.lock_version+=1;return json({...r.revision,response_id:r.id,answer_payload_hash:'x',validation_summary:{}},201)}
  if(path==='/api/v1/responses/resp1/validate'){const r=state.response!;const issues=options.validate?.(r.revision.answers)??[];r.revision={...r.revision,status:issues.length?'validation_failed':'validated',validation_issues:issues.map(i=>({...i,safe_params:{}}))};return json({...r.revision,response_id:r.id,answer_payload_hash:'x',validation_summary:{error_count:issues.length}})}
  if(path==='/api/v1/responses/resp1')return json(detail())
  if(path==='/api/v1/researches/r1/calculations'){state.calculations+=1;if(options.failFirstCalculation&&state.calculations===1)return Promise.reject(new TypeError('network down'));return json({id:'res1'})}
  if(path==='/api/v1/results/res1')return json({id:'res1',research_id:'r1',participant_id:'p1',response_revision_id:state.response?.revision.id,status:'complete',disclaimer_i18n:{'uz-Latn':'Bu natija tibbiy tashxis emas.'},calculated_at:'2026-10-02T10:00:00Z',result_hash:'abc1234567890000',scales:[],trace:[]})
  return json({})
 }
 return {calls,state,handler,posts:(suffix:string)=>calls.filter(c=>c.method==='POST'&&c.path.endsWith(suffix))}
}
function open(path:string,server:ReturnType<typeof fakeServer>){sessionStorage.setItem('psychogram_token','token');window.history.pushState({},'',path);vi.stubGlobal('fetch',vi.fn(server.handler));return render(<BrowserRouter><App/></BrowserRouter>)}
async function fillNew(){await userEvent.type(await screen.findByLabelText(/Respondent kodi/),'P001');await userEvent.click(screen.getByLabelText(/Respondent rozilik berdi/));await userEvent.type(screen.getByLabelText('Necha marta?'),'2');await userEvent.click(within(screen.getByRole('group',{name:'Kayfiyat'})).getByLabelText('Yaxshi'))}

beforeEach(()=>sessionStorage.clear())
afterEach(()=>{vi.unstubAllGlobals();sessionStorage.clear()})

describe('response form',()=>{
 it('records consent, saves, validates and scores a new respondent in one action',async()=>{
  const server=fakeServer();open('/researches/r1/responses/new',server);await fillNew();await userEvent.click(screen.getByRole('button',{name:'Natijani hisoblash'}))
  await waitFor(()=>expect(window.location.pathname).toBe('/results/res1'))
  expect(server.posts('/participants')[0].body).toEqual({external_code:'P001'})
  expect(server.posts('/consents')[0].body).toMatchObject({status:'granted',reference:'ETIKA-2026',version:'1.0'})
  expect(server.posts('/r1/responses')[0].body).toEqual({participant_id:'p1',attempt_key:'initial',answers:{q1:2,q2:'a'},finalize:false})
  expect(server.posts('/validate')).toHaveLength(1);expect(server.posts('/calculations')[0].body).toEqual({response_revision_id:'rev1',idempotency_key:'calc-rev1'})
 })

 it('does not create anything until consent is confirmed',async()=>{
  const server=fakeServer();open('/researches/r1/responses/new',server);await userEvent.type(await screen.findByLabelText(/Respondent kodi/),'P001');await userEvent.click(screen.getByRole('button',{name:'Qoralamani saqlash'}))
  expect(await screen.findByText(/roziligini qayd eting/)).toBeInTheDocument();expect(server.calls.filter(c=>c.method==='POST')).toHaveLength(0)
 })

 it('saves a draft and confirms only after the server does',async()=>{
  const server=fakeServer();open('/researches/r1/responses/new',server);await userEvent.type(await screen.findByLabelText(/Respondent kodi/),'P001');await userEvent.click(screen.getByLabelText(/Respondent rozilik berdi/));await userEvent.type(screen.getByLabelText('Necha marta?'),'1')
  await userEvent.click(screen.getByRole('button',{name:'Qoralamani saqlash'}));expect(await screen.findByText(/Qoralama serverda saqlandi \(revision 1\)/)).toBeInTheDocument()
  expect(window.location.pathname).toBe('/researches/r1/responses/resp1');expect(server.posts('/validate')).toHaveLength(0);expect(server.posts('/calculations')).toHaveLength(0)
 })

 it('shows validation errors next to the question and keeps the draft',async()=>{
  const server=fakeServer({validate:answers=>answers.q1===2?[{item_code:'q1',error_code:'VALUE_OUT_OF_RANGE'}]:[]});open('/researches/r1/responses/new',server);await fillNew();await userEvent.click(screen.getByRole('button',{name:'Natijani hisoblash'}))
  expect(await screen.findByText('Qiymat ruxsat etilgan oraliqdan tashqarida.')).toBeInTheDocument();expect(screen.getByLabelText('Necha marta?')).toHaveAttribute('aria-invalid','true');expect(screen.getByLabelText('Necha marta?')).toHaveValue('2')
  expect(server.posts('/calculations')).toHaveLength(0)
  await userEvent.clear(screen.getByLabelText('Necha marta?'));await userEvent.type(screen.getByLabelText('Necha marta?'),'3');await userEvent.click(screen.getByRole('button',{name:'Natijani hisoblash'}))
  await waitFor(()=>expect(window.location.pathname).toBe('/results/res1'));expect(server.posts('/participants')).toHaveLength(1);expect(server.posts('/r1/responses')).toHaveLength(1);expect(server.posts('/revisions')).toHaveLength(1)
  expect(server.posts('/calculations')[0].body).toEqual({response_revision_id:'rev2',idempotency_key:'calc-rev2'})
 })

 it('retries after a lost network response without creating duplicates',async()=>{
  const server=fakeServer({failFirstCalculation:true});open('/researches/r1/responses/new',server);await fillNew();await userEvent.click(screen.getByRole('button',{name:'Natijani hisoblash'}))
  expect(await screen.findByText(/NETWORK_UNAVAILABLE/)).toBeInTheDocument();await userEvent.click(screen.getByRole('button',{name:'Natijani hisoblash'}))
  await waitFor(()=>expect(window.location.pathname).toBe('/results/res1'))
  expect(server.posts('/participants')).toHaveLength(1);expect(server.posts('/consents')).toHaveLength(1);expect(server.posts('/r1/responses')).toHaveLength(1);expect(server.posts('/revisions')).toHaveLength(0)
  expect(server.posts('/calculations').map(c=>c.body?.idempotency_key)).toEqual(['calc-rev1','calc-rev1'])
 })

 it('refuses a code that already belongs to a respondent with answers and links to it',async()=>{
  const server=fakeServer({existing:true});open('/researches/r1/responses/new',server);await fillNew();await userEvent.click(screen.getByRole('button',{name:'Qoralamani saqlash'}))
  expect(await screen.findByText(/P001 kodli respondent allaqachon mavjud/)).toBeInTheDocument();expect(screen.getByRole('link',{name:/Mavjud javobni ochish/})).toHaveAttribute('href','/researches/r1/responses/resp1')
  expect(server.posts('/r1/responses')).toHaveLength(0);expect(server.posts('/consents')).toHaveLength(0)
 })

 it('reopens saved answers and asks for a reason before changing validated ones',async()=>{
  const server=fakeServer({existing:true});open('/researches/r1/responses/resp1',server)
  expect(await screen.findByLabelText('Necha marta?')).toHaveValue('3');expect(screen.getByLabelText(/Respondent kodi/)).toHaveValue('P001');expect(screen.getByText('Respondent roziligi qayd etilgan.')).toBeInTheDocument()
  expect(screen.queryByLabelText(/Tuzatish sababi/)).not.toBeInTheDocument();await userEvent.clear(screen.getByLabelText('Necha marta?'));await userEvent.type(screen.getByLabelText('Necha marta?'),'1')
  await userEvent.click(screen.getByRole('button',{name:'Qoralamani saqlash'}));expect(await screen.findByText(/tuzatish sababini yozing/)).toBeInTheDocument();expect(server.posts('/revisions')).toHaveLength(0)
  await userEvent.type(screen.getByLabelText(/Tuzatish sababi/),'Kiritishda xato');await userEvent.click(screen.getByRole('button',{name:'Qoralamani saqlash'}))
  expect(await screen.findByText(/revision 3/)).toBeInTheDocument();expect(server.posts('/revisions')[0].body).toEqual({answers:{q1:1,q2:'a'},expected_lock_version:2,correction_reason:'Kiritishda xato'})
 })
})

describe('responses workbench',()=>{
 it('shows answer and result status separately and links only a current result',async()=>{
  const row=(id:string,code:string,revisionStatus:string,resultStatus:string,resultId:string|null)=>({id,research_id:'r1',participant_id:`p-${id}`,participant_external_code:code,attempt_key:'initial',status:revisionStatus,lock_version:1,current_revision_id:`rev-${id}`,current_revision_number:1,current_revision_status:revisionStatus,created_at:'2026-10-02T10:00:00Z',result_status:resultStatus,current_result_id:resultId})
  const items=[row('a','P001','validated','calculated','res-a'),row('b','P002','validated','recalculation_required',null),row('c','P003','draft','not_calculated',null)]
  sessionStorage.setItem('psychogram_token','token');window.history.pushState({},'','/researches/r1/responses')
  vi.stubGlobal('fetch',vi.fn((input:RequestInfo|URL)=>{const path=String(input);if(path.includes('/auth/me'))return json(me);if(path.endsWith('/researches'))return json([research]);if(path.includes('/researches/r1/responses'))return json({items,total:3,offset:0,limit:20});return json({})}))
  render(<BrowserRouter><App/></BrowserRouter>)
  const rows=await screen.findAllByRole('row');const text=rows.slice(1).map(r=>r.textContent)
  expect(text[0]).toContain('P001');expect(text[0]).toContain('Hisoblangan');expect(text[1]).toContain('Qayta hisoblash kerak');expect(text[2]).toContain('Qoralama');expect(text[2]).toContain('Hisoblanmagan')
  expect(screen.getAllByRole('link',{name:'Natija'}).map(a=>a.getAttribute('href'))).toEqual(['/results/res-a'])
  expect(within(rows[2]).getByRole('link',{name:/Ochish/})).toHaveAttribute('href','/researches/r1/responses/b')
 })
})
