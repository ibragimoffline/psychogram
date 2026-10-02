import { useState } from 'react'

export function RemoteIcon({name,size=20,label,className='',color='#34443F'}:{name:string;size?:number;label?:string;className?:string;color?:string}){
  const [failed,setFailed]=useState(false)
  const style={width:size,height:size} as const
  return <span className={`remote-icon ${className}`} style={style} aria-hidden={label?undefined:true} role={label?'img':undefined} aria-label={label}>
    {failed?<span className="icon-fallback">{name.slice(0,1).toUpperCase()}</span>:<img src={`https://api.iconify.design/lucide/${encodeURIComponent(name)}.svg?color=${encodeURIComponent(color)}&width=${size}&height=${size}`} width={size} height={size} alt="" loading="lazy" referrerPolicy="no-referrer" crossOrigin="anonymous" onError={()=>setFailed(true)}/>} 
  </span>
}
