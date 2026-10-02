import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { BrowserRouter } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import App from '../App'

const profile=(role='researcher')=>({id:'u1',email:'r@example.com',full_name:'Researcher',is_platform_admin:false,memberships:[{organization_id:'org1',organization_name:'Lab',role,can_view_pii:false}]})
const research=(status:string)=>({id:'r1',tenant_id:'org1',name:'Pilot',purpose:'Test',status,methodology_version_id:'v1',pii_mode:'pseudonymous',consent_reference:'ETIKA',consent_version:'1'})
const json=(value:unknown,status=200,headers:Record<string,string>={})=>Promise.resolve(new Response(JSON.stringify(value),{status,headers:{'Content-Type':'application/json',...headers}}))
interface Call {method:string;path:string;body?:unknown}

function open(path:string,handler:(path:string,method:string,body:unknown)=>Promise<Response>|undefined,role='researcher'){
 const calls:Call[]=[]
 sessionStorage.setItem('psychogram_token','token');window.history.pushState({},'',path)
 vi.stubGlobal('fetch',vi.fn((input:RequestInfo|URL,init?:RequestInit)=>{const url=String(input);const method=init?.method??'GET';const body=init?.body?JSON.parse(String(init.body)):undefined;calls.push({method,path:url,body});if(url.includes('/auth/me'))return json(profile(role));return handler(url,method,body)??json({items:[],total:0,offset:0,limit:20})}))
 render(<BrowserRouter><App/></BrowserRouter>)
 return calls
}

beforeEach(()=>sessionStorage.clear())
afterEach(()=>{vi.unstubAllGlobals();vi.restoreAllMocks();sessionStorage.clear()})

describe('research lifecycle',()=>{
 it('closes a research after confirmation and stops new answers',async()=>{
  let status='active'
  const calls=open('/researches/r1/responses',(path,method)=>{if(path.endsWith('/researches/r1/close')&&method==='POST'){status='closed';return json(research(status))}if(path.endsWith('/researches'))return json([research(status)]);return undefined})
  expect(await screen.findByRole('link',{name:'Javob kiritish'})).toBeInTheDocument()
  await userEvent.click(screen.getByRole('button',{name:'Tadqiqotni yakunlash'}));await userEvent.click(await screen.findByRole('button',{name:'Ha, yakunlash'}))
  expect(await screen.findByText(/Tadqiqot yakunlandi/)).toBeInTheDocument();await waitFor(()=>expect(screen.getAllByText('Yakunlangan').length).toBeGreaterThan(0))
  expect(calls.filter(c=>c.path.endsWith('/close')).map(c=>c.body)).toEqual([{confirm_uncalculated:false}])
  expect(screen.queryByRole('button',{name:'Tadqiqotni yakunlash'})).not.toBeInTheDocument();expect(screen.queryByRole('link',{name:'Javob kiritish'})).not.toBeInTheDocument()
 })

 it('shows how many responses are uncalculated and closes only on explicit confirmation',async()=>{
  let status='active'
  const calls=open('/researches/r1',(path,method,body)=>{if(path.endsWith('/close')&&method==='POST'){if(!(body as {confirm_uncalculated:boolean}).confirm_uncalculated)return json({error:{code:'RESEARCH_HAS_UNCALCULATED_RESPONSES',message:'x',details:{uncalculated_responses:2}}},409);status='closed';return json(research(status))}if(path.endsWith('/researches'))return json([research(status)]);return undefined})
  await userEvent.click(await screen.findByRole('button',{name:'Tadqiqotni yakunlash'}));await userEvent.click(await screen.findByRole('button',{name:'Ha, yakunlash'}))
  expect(await screen.findByText(/2 ta respondentning joriy javobi hali hisoblanmagan/)).toBeInTheDocument();expect(screen.getByRole('link',{name:'Javoblarga qaytish'})).toHaveAttribute('href','/researches/r1/responses')
  await userEvent.click(screen.getByRole('button',{name:'Baribir yakunlash'}));expect(await screen.findByText(/Tadqiqot yakunlandi/)).toBeInTheDocument()
  expect(calls.filter(c=>c.path.endsWith('/close')).map(c=>c.body)).toEqual([{confirm_uncalculated:false},{confirm_uncalculated:true}])
 })

 it('downloads the research CSV and reports what it contained',async()=>{
  Object.defineProperty(URL,'createObjectURL',{value:vi.fn(()=>'blob:url'),configurable:true});Object.defineProperty(URL,'revokeObjectURL',{value:vi.fn(),configurable:true});vi.spyOn(HTMLAnchorElement.prototype,'click').mockImplementation(()=>undefined)
  open('/researches/r1',(path)=>{if(path.includes('/researches/r1/export?format=csv'))return Promise.resolve(new Response('participant_code\r\nP001\r\n',{status:200,headers:{'Content-Type':'text/csv','X-Export-Rows':'3','X-Export-Not-Calculated':'1','X-Export-Excluded-Consent':'0'}}));if(path.endsWith('/researches'))return json([research('closed')]);return undefined})
  await userEvent.click(await screen.findByRole('button',{name:'CSV yuklash'}))
  expect(await screen.findByText('CSV yuklandi: 3 ta respondent. Hali hisoblanmagan: 1. Rozilik sabab chiqarilmagan: 0.')).toBeInTheDocument()
 })

 it('hides close and research export from auditors',async()=>{
  open('/researches/r1',(path)=>path.endsWith('/researches')?json([research('active')]):undefined,'auditor')
  await screen.findByRole('heading',{name:'Pilot'});expect(screen.queryByRole('button',{name:'Tadqiqotni yakunlash'})).not.toBeInTheDocument();expect(screen.queryByRole('button',{name:'CSV yuklash'})).not.toBeInTheDocument()
 })
})

describe('result currency',()=>{
 const result=(isCurrent:boolean)=>({id:'res1',research_id:'r1',participant_id:'p1',participant_code:'P001',response_id:'resp1',response_revision_id:'rev1',is_current:isCurrent,methodology_name:'Demo metodika',version_code:'1.0.0',status:'complete',disclaimer_i18n:{'uz-Latn':'Bu natija tibbiy tashxis emas.'},calculated_at:'2026-10-02T10:00:00Z',result_hash:'abc1234567890000',scales:[],trace:[]})
 it('marks a result whose answers were corrected and links back to them',async()=>{
  open('/results/res1',(path)=>path.endsWith('/results/res1')?json(result(false)):undefined)
  expect(await screen.findByText('Bu natija joriy emas')).toBeInTheDocument();expect(screen.getByRole('link',{name:/Javobni ochish/})).toHaveAttribute('href','/researches/r1/responses/resp1')
  expect(screen.getByText('Respondent P001')).toBeInTheDocument();expect(screen.getByText(/Demo metodika/)).toBeInTheDocument()
 })
 it('shows no warning for the current result',async()=>{
  open('/results/res1',(path)=>path.endsWith('/results/res1')?json(result(true)):undefined)
  expect(await screen.findByText('Respondent P001')).toBeInTheDocument();expect(screen.queryByText('Bu natija joriy emas')).not.toBeInTheDocument()
 })
})
