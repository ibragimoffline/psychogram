import type { ApiErrorShape } from '../types'

const API_ORIGIN = (import.meta.env.VITE_API_ORIGIN as string | undefined)?.replace(/\/$/, '') ?? ''

export class ApiError extends Error {
  constructor(public status:number, public code:string, message:string, public details?:unknown){super(message)}
}

type ApiOptions = RequestInit & { token?:string|null; organizationId?:string|null; bodyJson?:unknown }

export async function api<T>(path:string, options:ApiOptions = {}):Promise<T>{
  const {token,organizationId,bodyJson,...init}=options
  const headers=new Headers(init.headers)
  headers.set('Accept','application/json')
  if(bodyJson!==undefined){headers.set('Content-Type','application/json')}
  if(token) headers.set('Authorization',`Bearer ${token}`)
  if(organizationId) headers.set('X-Organization-ID',organizationId)
  let response:Response
  try { response=await fetch(`${API_ORIGIN}${path}`,{...init,headers,body:bodyJson===undefined?init.body:JSON.stringify(bodyJson),referrerPolicy:'no-referrer'}) }
  catch { throw new ApiError(0,'NETWORK_UNAVAILABLE','Server bilan aloqa yo‘q. Ma’lumot saqlanmadi.') }
  if(!response.ok) throw await responseError(response,'So‘rovni bajarib bo‘lmadi.')
  if(response.status===204)return undefined as T
  return await response.json() as T
}

export async function download(path:string,token:string,organizationId:string,filename:string){
  let response:Response
  try{response=await fetch(`${API_ORIGIN}${path}`,{headers:{Authorization:`Bearer ${token}`,'X-Organization-ID':organizationId},referrerPolicy:'no-referrer'})}
  catch{throw new ApiError(0,'NETWORK_UNAVAILABLE','Server bilan aloqa yo‘q. Eksport yaratilmadi.')}
  if(!response.ok) throw await responseError(response,'Eksportni tayyorlab bo‘lmadi.')
  const url=URL.createObjectURL(await response.blob()); const anchor=document.createElement('a'); anchor.href=url;anchor.download=filename;anchor.click();URL.revokeObjectURL(url)
}

async function responseError(response:Response,fallback:string):Promise<ApiError>{
  let payload:ApiErrorShape={}
  try{payload=await response.clone().json() as ApiErrorShape}catch{/* non-JSON error bodies are never rendered */}
  return new ApiError(
    response.status,
    payload.error?.code ?? `HTTP_${response.status}`,
    payload.error?.message ?? fallback,
    payload.error?.details ?? payload.detail,
  )
}

export function safeMessage(error:unknown){return error instanceof ApiError ? `${error.message} (${error.code})` : 'Kutilmagan xato yuz berdi.'}
