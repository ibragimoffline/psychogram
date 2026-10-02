import { Component, type ReactNode } from 'react'
import { RemoteIcon } from './RemoteIcon'

interface Props { children:ReactNode }
interface State { failed:boolean }

export class ErrorBoundary extends Component<Props,State>{
  state:State={failed:false}
  static getDerivedStateFromError():State{return{failed:true}}
  componentDidCatch(){/* Raw error and component data intentionally never rendered or logged. */}
  render(){if(!this.state.failed)return this.props.children;return <main className="fatal-recovery" role="alert"><RemoteIcon name="circle-x" size={28}/><p className="eyebrow">Xavfsiz tiklash</p><h1>Interfeysni ochib bo‘lmadi</h1><p>Maxfiy ma’lumot ko‘rsatilmagan. Sahifani xavfsiz qayta yuklang yoki kirish ekraniga qayting.</p><div className="button-row"><button className="button primary" onClick={()=>window.location.reload()}>Sahifani qayta yuklash</button><button className="button secondary" onClick={()=>{sessionStorage.clear();window.location.assign('/login')}}>Sessiyani yopish</button></div></main>}
}
