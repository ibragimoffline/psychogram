import { useQuery, useQueryClient } from '@tanstack/react-query'
import { useEffect, useRef, useState, type FormEvent } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { Button, ErrorSummary, Field, LiveStatus, Loading, Notice, Status } from '../components/UI'
import { useApi, useAuth } from '../context/AuthContext'
import { ApiError, safeMessage } from '../lib/api'
import { can } from '../lib/capabilities'
import { tenantKey } from '../lib/queryKeys'
import type { InstrumentItem, Page as DataPage, Participant, Research, ResponseDetail, ResponseItem, Revision, ValidationIssue, Version } from '../types'

const VALID_CONSENT=['granted','not_required_with_basis']
export const ISSUE_TEXT:Record<string,string>={ITEM_REQUIRED:'Bu savolga javob berilishi shart.',OPTION_NOT_ALLOWED:'Bu javob varianti ruxsat etilmagan.',VALUE_OUT_OF_RANGE:'Qiymat ruxsat etilgan oraliqdan tashqarida.',STEP_INVALID:'Qiymat ruxsat etilgan qadamga mos emas.',TYPE_INVALID:'Qiymat turi noto‘g‘ri.',BOOLEAN_LITERAL_INVALID:'“Ha” yoki “Yo‘q”ni tanlang.',UNKNOWN_ITEM:'Metodikada bunday savol yo‘q.'}
const issueText=(code:string)=>ISSUE_TEXT[code]??code

interface Saved {responseId:string;lockVersion:number;revisionId:string;revisionNumber:number;revisionStatus:string;answersKey:string}
class FlowStop extends Error {constructor(message:string,public existingResponseId?:string){super(message)}}

function canonical(item:InstrumentItem,raw:string):unknown{const text=raw.trim();if(item.item_type==='integer')return /^-?\d+$/.test(text)?Number(text):text;if(item.item_type==='boolean')return text==='true'?true:text==='false'?false:text;return text}
function toRaw(value:unknown){return value===null||value===undefined?'':String(value)}
function answersFor(items:InstrumentItem[],raw:Record<string,string>){const answers:Record<string,unknown>={};for(const item of items){const value=raw[item.item_code]??'';if(value.trim()!=='')answers[item.item_code]=canonical(item,value)}return answers}
const keyOf=(answers:Record<string,unknown>)=>JSON.stringify(Object.keys(answers).sort().map(key=>[key,answers[key]]))
const today=()=>new Date().toISOString().slice(0,10)

// One form for entering, saving and scoring a respondent's answers. Each step reuses what the
// server already has (participant, consent, response, idempotency key), so pressing again after an
// error or a lost network response never creates duplicates.
export function ResponseForm(){
 // 'new' and a saved response share one route so the form keeps its state when the URL gains the id.
 const {researchId='',responseId:param}=useParams();const routeResponseId=param==='new'?undefined:param;const call=useApi();const qc=useQueryClient();const navigate=useNavigate();const {membership}=useAuth();const org=membership?.organization_id
 const researches=useQuery({queryKey:tenantKey(org,'researches'),queryFn:()=>call<Research[]>('/api/v1/researches')});const research=researches.data?.find(r=>r.id===researchId)
 const version=useQuery({queryKey:tenantKey(org,'version',research?.methodology_version_id,researchId),enabled:Boolean(research),queryFn:()=>call<Version>(`/api/v1/methodology-versions/${research?.methodology_version_id}?research_id=${researchId}`)})
 // Once this form has saved, its own state is the latest server state; refetching would only blank the form.
 const [saved,setSaved]=useState<Saved|null>(null)
 const existing=useQuery({queryKey:tenantKey(org,'response',routeResponseId),enabled:Boolean(routeResponseId)&&!saved,queryFn:()=>call<ResponseDetail>(`/api/v1/responses/${routeResponseId}`)})
 const existingParticipant=useQuery({queryKey:tenantKey(org,'participant',researchId,existing.data?.participant_id),enabled:Boolean(existing.data),queryFn:()=>call<Participant>(`/api/v1/researches/${researchId}/participants/${existing.data?.participant_id}`)})
 const items=version.data?.snapshot?.items??[]

 const [code,setCode]=useState('');const [participantId,setParticipantId]=useState<string|null>(null);const [consentValid,setConsentValid]=useState(false)
 const [consentConfirmed,setConsentConfirmed]=useState(false);const [consentReference,setConsentReference]=useState('');const [consentVersion,setConsentVersion]=useState('');const [consentDate,setConsentDate]=useState(today)
 const [raw,setRaw]=useState<Record<string,string>>({});const [reason,setReason]=useState('')
 const [issues,setIssues]=useState<ValidationIssue[]>([]);const [error,setError]=useState('');const [existingLink,setExistingLink]=useState('');const [status,setStatus]=useState('');const [busy,setBusy]=useState(false)
 const initialized=useRef(false)

 useEffect(()=>{if(research&&!consentReference){setConsentReference(research.consent_reference??'');setConsentVersion(research.consent_version??'')}},[research,consentReference])
 useEffect(()=>{const data=existing.data;const revision=data?.current_revision;if(initialized.current||!data||!revision||!existingParticipant.data)return;initialized.current=true
  setCode(data.participant_external_code);setParticipantId(data.participant_id);setConsentValid(VALID_CONSENT.includes(existingParticipant.data.current_consent_status??''))
  setRaw(Object.fromEntries(Object.entries(revision.answers??{}).map(([key,value])=>[key,toRaw(value)])))
  setSaved({responseId:data.id,lockVersion:data.lock_version,revisionId:revision.id,revisionNumber:revision.revision_number,revisionStatus:revision.status,answersKey:keyOf(revision.answers??{})});setIssues(revision.validation_issues??[])},[existing.data,existingParticipant.data])

 const writable=can(membership?.role,'response:write');const canCalculate=can(membership?.role,'result:calculate');const active=research?.status==='active'
 const changed=saved?keyOf(answersFor(items,raw))!==saved.answersKey:true;const needsReason=Boolean(saved&&saved.revisionStatus==='validated'&&changed)
 const itemIssues=(itemCode:string)=>issues.filter(issue=>issue.item_code===itemCode).map(issue=>issueText(issue.error_code)).join(' ')||undefined
 const generalIssues=issues.filter(issue=>!issue.item_code||!items.some(item=>item.item_code===issue.item_code))

 async function ensureParticipant():Promise<string>{
  if(participantId)return participantId
  const external=code.trim()
  try{const created=await call<Participant>(`/api/v1/researches/${researchId}/participants`,{method:'POST',bodyJson:{external_code:external}});setParticipantId(created.id);return created.id}
  catch(err){
   if(!(err instanceof ApiError&&err.code==='PARTICIPANT_CODE_EXISTS'))throw err
   // The code exists: reuse it unless it already has answers, which belong to another respondent record.
   const found=(await call<DataPage<Participant>>(`/api/v1/researches/${researchId}/participants?limit=100&query=${encodeURIComponent(external)}`)).items.find(p=>p.external_code===external)
   if(!found)throw err
   const answered=await call<DataPage<ResponseItem>>(`/api/v1/researches/${researchId}/responses?participant_id=${found.id}`)
   if(answered.items.length)throw new FlowStop(`${external} kodli respondent allaqachon mavjud va javobi bor.`,answered.items[0].id)
   setParticipantId(found.id);setConsentValid(VALID_CONSENT.includes(found.current_consent_status??''));return found.id}
 }
 async function ensureConsent(id:string){
  if(consentValid)return
  if(!consentConfirmed)throw new FlowStop('Javobni saqlashdan oldin respondent roziligini qayd eting.')
  await call(`/api/v1/participants/${id}/consents`,{method:'POST',bodyJson:{status:'granted',reference:consentReference.trim(),version:consentVersion.trim(),obtained_at:new Date(`${consentDate}T00:00:00`).toISOString()}});setConsentValid(true)
 }
 async function adoptExistingResponse(id:string):Promise<Saved>{
  const listed=(await call<DataPage<ResponseItem>>(`/api/v1/researches/${researchId}/responses?participant_id=${id}`)).items[0]
  const detail=await call<ResponseDetail>(`/api/v1/responses/${listed.id}`);const revision=detail.current_revision as Revision
  return {responseId:detail.id,lockVersion:detail.lock_version,revisionId:revision.id,revisionNumber:revision.revision_number,revisionStatus:revision.status,answersKey:keyOf(revision.answers??{})}
 }
 async function saveAnswers(id:string):Promise<Saved>{
  const answers=answersFor(items,raw);const key=keyOf(answers);let current=saved
  if(!current){
   try{const created=await call<{id:string;lock_version:number;current_revision_id:string}>(`/api/v1/researches/${researchId}/responses`,{method:'POST',bodyJson:{participant_id:id,attempt_key:'initial',answers,finalize:false}});current={responseId:created.id,lockVersion:created.lock_version,revisionId:created.current_revision_id,revisionNumber:1,revisionStatus:'draft',answersKey:key}}
   catch(err){if(!(err instanceof ApiError&&err.code==='RESPONSE_ATTEMPT_EXISTS'))throw err;current=await adoptExistingResponse(id)}
  }
  if(current.answersKey!==key){
   if(current.revisionStatus==='validated'&&!reason.trim())throw new FlowStop('Tasdiqlangan javobni o‘zgartirish uchun tuzatish sababini yozing.')
   const revision=await call<Revision>(`/api/v1/responses/${current.responseId}/revisions`,{method:'POST',bodyJson:{answers,expected_lock_version:current.lockVersion,correction_reason:current.revisionStatus==='validated'?reason.trim():undefined}})
   current={...current,lockVersion:current.lockVersion+1,revisionId:revision.id,revisionNumber:revision.revision_number,revisionStatus:revision.status,answersKey:key};setReason('')
  }
  setSaved(current);initialized.current=true
  if(!routeResponseId)navigate(`/researches/${researchId}/responses/${current.responseId}`,{replace:true})
  return current
 }
 async function run(step:'save'|'validate'|'calculate'){
  setBusy(true);setError('');setExistingLink('');setStatus('')
  try{
   if(!participantId&&!consentConfirmed)throw new FlowStop('Javobni saqlashdan oldin respondent roziligini qayd eting.')
   const id=await ensureParticipant();await ensureConsent(id);let current=await saveAnswers(id)
   await qc.invalidateQueries({queryKey:tenantKey(org,'responses',researchId)})
   if(step==='save'){setStatus(`Qoralama serverda saqlandi (revision ${current.revisionNumber}).`);return}
   if(current.revisionStatus!=='validated'){
    const revision=await call<Revision>(`/api/v1/responses/${current.responseId}/validate`,{method:'POST'})
    current={...current,revisionStatus:revision.status};setSaved(current);setIssues(revision.validation_issues??[])
    if(revision.status!=='validated'){setError(`${revision.validation_issues?.length??0} ta javobda xato bor. Belgilangan savollarni tuzating.`);return}
   }else setIssues([])
   if(step==='validate'){setStatus('Javoblar tekshirildi va tasdiqlandi.');return}
   const result=await call<{id:string}>(`/api/v1/researches/${researchId}/calculations`,{method:'POST',bodyJson:{response_revision_id:current.revisionId,idempotency_key:`calc-${current.revisionId}`}})
   await qc.invalidateQueries({queryKey:tenantKey(org,'responses',researchId)});navigate(`/results/${result.id}`)
  }catch(err){
   if(err instanceof FlowStop){setError(err.message);if(err.existingResponseId)setExistingLink(`/researches/${researchId}/responses/${err.existingResponseId}`)}
   else if(err instanceof ApiError&&err.code==='REVISION_CONFLICT')setError('Bu javob boshqa oynada o‘zgartirilgan. Sahifani yangilab, qaytadan urinib ko‘ring.')
   else setError(safeMessage(err))
  }finally{setBusy(false)}
 }
 function submit(e:FormEvent<HTMLFormElement>){e.preventDefault();void run(canCalculate?'calculate':'validate')}
 function setAnswer(itemCode:string,value:string){setRaw(current=>({...current,[itemCode]:value}));setIssues(current=>current.filter(issue=>issue.item_code!==itemCode))}

 if(researches.isLoading||version.isLoading||existing.isLoading||existingParticipant.isLoading)return <Loading label="Forma tayyorlanmoqda"/>
 if(!research)return <Notice tone="warning" title="Tadqiqot topilmadi">Ro‘yxatga qaytib, tadqiqotni qayta oching.</Notice>
 const promptsAllowed=Boolean(version.data?.licence?.allow_item_display)
 return <section className="route-section"><Link className="back-action" to={`/researches/${researchId}/responses`}>← Javoblar</Link>
  <header className="section-header"><div><p className="eyebrow">{version.data?.methodology_name} · v{version.data?.version_code}</p><h2>{saved?`Respondent ${code}`:'Yangi respondent javobi'}</h2></div>{saved&&<Status value={saved.revisionStatus}/>}</header>
  {!active&&<Notice tone="warning" title="Tadqiqot faol emas">Javob kiritish faqat boshlangan tadqiqotda mumkin.</Notice>}
  {!writable&&<Notice title="Faqat o‘qish">Sizning rolingiz javob kirita olmaydi.</Notice>}
  <form className="instrument" onSubmit={submit} noValidate aria-describedby={error?'response-error':undefined}>
   <ErrorSummary id="response-error" error={error} title="Amal bajarilmadi"/>{existingLink&&<p><Link to={existingLink}>Mavjud javobni ochish →</Link></p>}
   {generalIssues.length>0&&<Notice tone="danger" title="Umumiy xatolar">{generalIssues.map(issue=>`${issue.item_code??''} ${issueText(issue.error_code)}`).join(' ')}</Notice>}
   {status&&<LiveStatus><Notice tone="success" title="Server tasdiqladi">{status}</Notice></LiveStatus>}
   <section><h3>01 · Respondent</h3><Field label="Respondent kodi" hint="Masalan, P001. Ism yoki telefon kiritmang."><input value={code} onChange={e=>setCode(e.target.value)} required maxLength={120} readOnly={Boolean(participantId)} autoComplete="off"/></Field></section>
   <section><h3>02 · Rozilik</h3>{consentValid?<p className="muted">Respondent roziligi qayd etilgan.</p>:<><label className="choice"><input type="checkbox" checked={consentConfirmed} onChange={e=>setConsentConfirmed(e.target.checked)}/> Respondent rozilik berdi va bu hujjatlashtirilgan</label><div className="form-grid"><Field label="Rozilik hujjati"><input value={consentReference} onChange={e=>setConsentReference(e.target.value)} required maxLength={1000}/></Field><Field label="Rozilik shakli versiyasi"><input value={consentVersion} onChange={e=>setConsentVersion(e.target.value)} required maxLength={64}/></Field><Field label="Rozilik sanasi"><input type="date" value={consentDate} onChange={e=>setConsentDate(e.target.value)} required max={today()}/></Field></div></>}</section>
   <section><h3>03 · Savollar</h3>{!promptsAllowed&&<Notice tone="warning" title="Savol matnlari ko‘rsatilmaydi">Litsenziya savol matnini ekranda ko‘rsatishga ruxsat bermaydi. Javoblarni qog‘oz shakldan savol kodi bo‘yicha kiriting.</Notice>}
    <ol className="instrument-list">{items.map((item,index)=><li key={item.item_code}><span className="item-number">{String(index+1).padStart(2,'0')}</span><div><p className="item-code">{item.item_code}{item.required?' · majburiy':''}</p><ItemInput item={item} value={raw[item.item_code]??''} error={itemIssues(item.item_code)} onChange={value=>setAnswer(item.item_code,value)}/></div></li>)}</ol></section>
   {needsReason&&<Field label="Tuzatish sababi" hint="Tasdiqlangan javob o‘zgarmoqda; oldingi natija tarixda saqlanadi."><textarea value={reason} onChange={e=>setReason(e.target.value)} rows={2} maxLength={2000} required/></Field>}
   <div className="sticky-actions"><span>{saved?`Revision ${saved.revisionNumber}${changed?' · saqlanmagan o‘zgarishlar bor':''}`:'Hali saqlanmagan'}</span><Button type="button" variant="secondary" disabled={busy||!writable||!active||!code.trim()} onClick={()=>void run('save')}>Qoralamani saqlash</Button><Button type="submit" disabled={busy||!writable||!active||!code.trim()}>{busy?'Bajarilmoqda…':canCalculate?'Natijani hisoblash':'Tekshirish'}</Button></div>
  </form>
  {saved&&<p className="muted"><Link to={`/responses/${saved.responseId}`}>Revision tafsilotlari →</Link></p>}
 </section>
}

function ItemInput({item,value,error,onChange}:{item:InstrumentItem;value:string;error?:string;onChange:(value:string)=>void}){
 const label=item.prompt_i18n?.['uz-Latn']??item.prompt_i18n?.en??`Savol ${item.item_code}`
 const choices=item.item_type==='boolean'?[{option_code:'true',label:'Ha'},{option_code:'false',label:'Yo‘q'}]:item.item_type==='single_choice'&&item.options?.length?item.options.map(o=>({option_code:o.option_code,label:o.label_i18n?.['uz-Latn']??o.option_code})):null
 if(choices)return <fieldset aria-invalid={error?true:undefined} aria-describedby={error?`${item.item_code}-error`:undefined}><legend>{label}</legend>{choices.map(choice=><label className="choice" key={choice.option_code}><input type="radio" name={item.item_code} value={choice.option_code} checked={value===choice.option_code} onChange={()=>onChange(choice.option_code)}/>{choice.label}</label>)}{error&&<span className="field-error" id={`${item.item_code}-error`}>{error}</span>}</fieldset>
 return <Field label={label} error={error} hint={item.item_type==='single_choice'?'Javob varianti kodini kiriting':undefined}><input value={value} onChange={e=>onChange(e.target.value)} inputMode={item.item_type==='integer'?'numeric':item.item_type==='decimal'?'decimal':undefined} autoComplete="off"/></Field>
}
