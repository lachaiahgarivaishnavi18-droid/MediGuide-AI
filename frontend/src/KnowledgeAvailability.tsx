import { useEffect,useState } from 'react'
import { api } from './api'

export default function KnowledgeAvailability(){
  const [status,setStatus]=useState<{available_documents:number;approved_chunks:number}|null>(null)
  useEffect(()=>{const controller=new AbortController();api.get('/knowledge/status',{signal:controller.signal}).then(r=>setStatus(r.data)).catch(()=>{});return()=>controller.abort()},[])
  if(!status)return null
  return <div className={status.approved_chunks?'knowledge-availability':'notice warning'} role="status">
    {status.approved_chunks ? `${status.available_documents} available source documents · ${status.approved_chunks} approved passages` : 'No approved source passages are available. An administrator must import and review trusted references before medical questions can be answered.'}
  </div>
}
