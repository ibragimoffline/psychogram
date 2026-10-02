import { AnimatePresence, motion, useReducedMotion } from 'motion/react'
import {
  cloneElement,
  isValidElement,
  useEffect,
  useId,
  useRef,
  type ButtonHTMLAttributes,
  type KeyboardEvent,
  type ReactElement,
  type ReactNode,
} from 'react'
import { createPortal } from 'react-dom'
import { safeMessage } from '../lib/api'
import { RemoteIcon } from './RemoteIcon'

export function Button({variant='primary',icon,children,...props}:ButtonHTMLAttributes<HTMLButtonElement>&{variant?:'primary'|'secondary'|'quiet'|'danger';icon?:string}){
  return <button className={`button ${variant}`} {...props}>{icon&&<RemoteIcon name={icon} size={18} color={variant==='primary'||variant==='danger'?'#FFFFFF':'#34443F'}/>}<span>{children}</span></button>
}

export function Status({value}:{value:string|null|undefined}){const normalized=(value??'unknown').toLowerCase();return <span className={`status status-${normalized.replaceAll('_','-')}`}><span className="status-dot"/>{human(normalized)}</span>}
export const human=(value:string)=>({active:'Faol',ready:'Boshlashga tayyor',closed:'Yakunlangan',not_calculated:'Hisoblanmagan',calculated:'Hisoblangan',recalculation_required:'Qayta hisoblash kerak',scored:'Hisoblangan',draft:'Qoralama',validated:'Tekshirilgan',validation_failed:'Xatoli',complete:'Tayyor',completed:'Tayyor',granted:'Rozilik berilgan',declined:'Rad etilgan',withdrawn:'Qaytarib olingan',verified:'Tasdiqlangan',published:'Nashr qilingan',pseudonymous:'Pseudonim',anonymous:'Anonim',identified:'Identifikatsiyalangan'}[value]??value.replaceAll('_',' '))

export function Notice({tone='info',title,children}:{tone?:'info'|'warning'|'danger'|'success'|'privacy';title:string;children?:ReactNode}){
  return <div className={`notice ${tone}`}><RemoteIcon name={tone==='danger'?'circle-x':tone==='warning'?'triangle-alert':tone==='success'?'circle-check':tone==='privacy'?'shield':'info'} size={20}/><div><strong>{title}</strong>{children&&<div>{children}</div>}</div></div>
}

export function ErrorSummary({error,title='Amal bajarilmadi',id}:{error:unknown;title?:string;id?:string}){
  const ref=useRef<HTMLDivElement>(null)
  const message=typeof error==='string'?error:safeMessage(error)
  useEffect(()=>{if(message)ref.current?.focus()},[message])
  if(!message)return null
  return <div ref={ref} id={id} className="notice danger error-summary" role="alert" tabIndex={-1}><RemoteIcon name="circle-x" size={20}/><div><strong>{title}</strong><div>{message}</div></div></div>
}

export function ErrorNotice({error}:{error:unknown}){return <ErrorSummary error={error}/>}
export function LiveStatus({children,assertive=false}:{children:ReactNode;assertive?:boolean}){return <div className="live-status" role={assertive?'alert':'status'} aria-live={assertive?'assertive':'polite'} aria-atomic="true">{children}</div>}
export function Empty({icon='inbox',title,children,action}:{icon?:string;title:string;children:ReactNode;action?:ReactNode}){return <div className="empty"><RemoteIcon name={icon} size={28}/><h2>{title}</h2><p>{children}</p>{action}</div>}
export function Page({eyebrow,title,actions,children}:{eyebrow?:string;title:string;actions?:ReactNode;children:ReactNode}){const reduce=useReducedMotion();return <motion.div className="page" initial={reduce?{opacity:0}:{opacity:0,y:6}} animate={{opacity:1,y:0}} transition={{duration:reduce?.08:.22}}><header className="page-header"><div>{eyebrow&&<p className="eyebrow">{eyebrow}</p>}<h1>{title}</h1></div>{actions&&<div className="page-actions">{actions}</div>}</header>{children}</motion.div>}
export function Loading({label='Ma’lumot olinmoqda'}:{label?:string}){return <div className="loading" role="status"><span className="spinner"/>{label}</div>}

function focusable(panel:HTMLElement|null){return [...(panel?.querySelectorAll<HTMLElement>('button:not([disabled]),input:not([disabled]),select:not([disabled]),textarea:not([disabled]),a[href],[tabindex]:not([tabindex="-1"])')??[])]}
function trap(event:KeyboardEvent<HTMLElement>,panel:HTMLElement|null,onEscape:()=>void){
  if(event.key==='Escape'){event.preventDefault();onEscape();return}
  if(event.key!=='Tab')return
  const items=focusable(panel);if(!items.length)return
  const first=items[0],last=items[items.length-1]
  if(event.shiftKey&&document.activeElement===first){event.preventDefault();last.focus()}
  else if(!event.shiftKey&&document.activeElement===last){event.preventDefault();first.focus()}
}

export function Drawer({open,title,onClose,children}:{open:boolean;title:string;onClose:()=>void;children:ReactNode}){
  const reduce=useReducedMotion();const panel=useRef<HTMLElement>(null);const opener=useRef<HTMLElement|null>(null)
  useEffect(()=>{if(!open)return;opener.current=document.activeElement as HTMLElement;const timer=window.setTimeout(()=>focusable(panel.current)[0]?.focus(),0);return()=>{window.clearTimeout(timer);opener.current?.focus()}},[open])
  const offset=reduce?0:30;const duration=reduce?.08:.22
  return <AnimatePresence>{open&&<><motion.button aria-label="Panelni yopish" className="scrim" onClick={onClose} initial={{opacity:0}} animate={{opacity:1}} exit={{opacity:0}} transition={{duration:reduce?.08:.16}}/><motion.aside ref={panel} className="drawer" role="dialog" aria-modal="true" aria-label={title} onKeyDown={event=>trap(event,panel.current,onClose)} initial={{x:offset,opacity:0}} animate={{x:0,opacity:1}} exit={{x:offset,opacity:0}} transition={{duration}}><header><h2>{title}</h2><Button variant="quiet" onClick={onClose}>Yopish</Button></header>{children}</motion.aside></>}</AnimatePresence>
}

export function ConfirmAction({open,title,description,confirmLabel,onConfirm,onCancel,busy=false}:{open:boolean;title:string;description:string;confirmLabel:string;onConfirm:()=>void|Promise<void>;onCancel:()=>void;busy?:boolean}){
  const titleId=useId(),descriptionId=useId();const panel=useRef<HTMLElement>(null);const opener=useRef<HTMLElement|null>(null);const reduce=useReducedMotion()
  useEffect(()=>{if(!open)return;opener.current=document.activeElement as HTMLElement;const root=document.getElementById('root');if(root)root.inert=true;const timer=window.setTimeout(()=>panel.current?.querySelector<HTMLElement>('[data-cancel]')?.focus(),0);return()=>{window.clearTimeout(timer);if(root)root.inert=false;opener.current?.focus()}},[open])
  if(typeof document==='undefined')return null
  return createPortal(<AnimatePresence>{open&&<><motion.button aria-label="Tasdiqlash oynasini yopish" className="scrim" onClick={onCancel} initial={{opacity:0}} animate={{opacity:1}} exit={{opacity:0}} transition={{duration:reduce?.08:.16}}/><motion.section ref={panel} className="confirm-dialog" role="alertdialog" aria-modal="true" aria-labelledby={titleId} aria-describedby={descriptionId} onKeyDown={event=>trap(event,panel.current,onCancel)} initial={reduce?{opacity:0}:{opacity:0,y:8}} animate={{opacity:1,y:0}} exit={{opacity:0}} transition={{duration:reduce?.08:.22}}><h2 id={titleId}>{title}</h2><p id={descriptionId}>{description}</p><div className="button-row"><Button type="button" variant="secondary" data-cancel onClick={onCancel} disabled={busy}>Bekor qilish</Button><Button type="button" variant="danger" onClick={onConfirm} disabled={busy}>{busy?'O‘chirilmoqda…':confirmLabel}</Button></div></motion.section></>}</AnimatePresence>,document.body)
}

type FieldControl={id?:string;'aria-describedby'?:string;'aria-invalid'?:boolean}
export function Field({label,hint,error,children}:{label:string;hint?:string;error?:string;children:ReactElement<FieldControl>}){
  const generated=useId();const inputId=children.props.id??`${generated}-input`;const hintId=`${generated}-hint`;const errorId=`${generated}-error`
  const described=[children.props['aria-describedby'],hint?hintId:null,error?errorId:null].filter(Boolean).join(' ')||undefined
  const control=isValidElement(children)?cloneElement(children,{id:inputId,'aria-describedby':described,'aria-invalid':error?true:children.props['aria-invalid']}):children
  return <div className="field"><label htmlFor={inputId}><span>{label}</span></label>{control}{hint&&<small id={hintId}>{hint}</small>}{error&&<span className="field-error" id={errorId}>{error}</span>}</div>
}

export function Pagination({offset,limit,total,onChange}:{offset:number;limit:number;total:number;onChange:(offset:number)=>void}){
  if(total<=limit)return null
  const start=total?offset+1:0,end=Math.min(offset+limit,total)
  return <nav className="pagination" aria-label="Sahifalash"><span>{start}–{end} / {total}</span><div className="button-row"><Button type="button" variant="secondary" disabled={offset===0} onClick={()=>onChange(Math.max(0,offset-limit))}>Oldingi</Button><Button type="button" variant="secondary" disabled={offset+limit>=total} onClick={()=>onChange(offset+limit)}>Keyingi</Button></div></nav>
}
