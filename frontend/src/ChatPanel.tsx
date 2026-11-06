import { useEffect,useLayoutEffect,useRef,useState,type FormEvent } from 'react'
import { useSearchParams } from 'react-router-dom'
import ReactMarkdown,{type Components} from 'react-markdown'
import { ArrowRight,Check,Clipboard,HeartPulse,LoaderCircle,MessageSquare,Plus,Send,ShieldCheck,Sparkles,Trash2,TriangleAlert } from 'lucide-react'
import { api,errorText } from './api'
import { parseChatResponse,parseMessages } from './chatProtocol'
import type { Conversation,Message,User } from './types'
import CitationDetails from './CitationDetails'
import KnowledgeAvailability from './KnowledgeAvailability'

const markdown:Components={img:()=>null,a:({href,children})=><a href={href} target="_blank" rel="noreferrer">{children}</a>}

export default function ChatPanel({user}:{user:User}){
  const [params,setParams]=useSearchParams(),id=params.get('conversation')
  const [messages,setMessages]=useState<Message[]>([]),[query,setQuery]=useState(''),[busy,setBusy]=useState(false),[loading,setLoading]=useState(false),[error,setError]=useState(''),[copied,setCopied]=useState('')
  const [history,setHistory]=useState<Conversation[]>([]),[suggestions,setSuggestions]=useState<string[]>([])
  const epoch=useRef(0),loadedConversation=useRef<string|null>(null),latest=useRef<HTMLElement|null>(null)
  const refreshHistory=()=>api.get<Conversation[]>('/conversations').then(r=>{
    if(!Array.isArray(r.data)||!r.data.every(c=>c&&typeof c.id==='string'&&typeof c.title==='string'))throw new Error('The server returned an invalid conversation list.')
    setHistory(r.data)
  }).catch(e=>setError(errorText(e)))
  useEffect(()=>{
    void refreshHistory()
    const controller=new AbortController()
    api.get<string[]>('/chat/suggestions',{signal:controller.signal}).then(r=>setSuggestions(Array.isArray(r.data)?r.data.filter(s=>typeof s==='string'):[])).catch(()=>{})
    return()=>controller.abort()
  },[])
  useLayoutEffect(()=>{
    const controller=new AbortController()
    // A URL update after the POST is an acknowledgement of the already loaded
    // conversation, not a navigation that may invalidate the next reply.
    if(id&&loadedConversation.current===id){setLoading(false);return()=>controller.abort()}
    const current=++epoch.current
    setError('')
    if(!id){loadedConversation.current=null;setMessages([]);setLoading(false);return()=>controller.abort()}
    setLoading(true);setMessages([])
    api.get('/chat/'+encodeURIComponent(id)+'/messages',{signal:controller.signal}).then(r=>{
      if(current!==epoch.current)return
      setMessages(parseMessages(r.data));loadedConversation.current=id
    }).catch(e=>{if(!controller.signal.aborted&&current===epoch.current)setError(errorText(e))}).finally(()=>{if(current===epoch.current)setLoading(false)})
    return()=>controller.abort()
  },[id])
  useEffect(()=>{latest.current?.scrollIntoView?.({block:'start',behavior:'smooth'})},[messages.length])

  async function send(text=query){
    const question=text.trim()
    if(question.length<2||busy||loading)return
    const current=epoch.current
    setBusy(true);setError('')
    try{
      const response=parseChatResponse((await api.post('/chat',{query:question,conversation_id:id??loadedConversation.current})).data)
      if(current!==epoch.current)return
      // Render the validated POST result directly. A second history fetch must
      // never replace a new answer with an older conversation snapshot.
      setMessages(previous=>[...previous,{id:'local-user:'+response.message_id,role:'user',content:question},{id:response.message_id,role:'assistant',content:response.answer,response}])
      loadedConversation.current=response.conversation_id
      setQuery('')
      if(id!==response.conversation_id)setParams({conversation:response.conversation_id},{replace:!id})
      void refreshHistory()
    }catch(e){if(current===epoch.current)setError(errorText(e))}finally{setBusy(false)}
  }
  async function clear(){if(!id||busy)return;try{await api.delete('/conversations/'+id);loadedConversation.current=null;setParams({});void refreshHistory()}catch(e){setError(errorText(e))}}
  async function copy(m:Message){try{await navigator.clipboard.writeText(m.content);setCopied(m.id);setTimeout(()=>setCopied(''),1800)}catch{setError('Clipboard unavailable. You can select and copy the answer text.')}}
  const submit=(e:FormEvent)=>{e.preventDefault();void send()}
  return <><KnowledgeAvailability/><div className={user.preferences.compact_answers?'chat-layout compact':'chat-layout'}>
    <aside className="chat-history panel"><button className="secondary" disabled={busy} onClick={()=>{loadedConversation.current=null;setParams({})}}><Plus size={16}/> New conversation</button><span className="nav-label">RECENT CONVERSATIONS</span>{history.map(c=><button disabled={busy} className={'history-item '+(id===c.id?'selected':'')} key={c.id} onClick={()=>setParams({conversation:c.id})}><MessageSquare size={15}/><span>{c.title}</span></button>)}</aside>
    <section className="chat-panel panel"><div className="chat-top"><span><span className="dot"/> MediGuide assistant</span>{id&&<button className="text-button" disabled={busy} onClick={clear}><Trash2 size={15}/> Delete conversation</button>}</div>
      <div className="chat-messages" aria-live="polite" aria-busy={busy||loading}>
        {loading&&<div className="loading"><LoaderCircle className="spin" size={18}/> Loading conversation…</div>}
        {!messages.length&&!busy&&!loading&&<div className="chat-welcome"><span className="big-icon"><Sparkles size={29}/></span><h2>What would you like to understand?</h2><p>Choose a question supported by the available references, or ask about a medicine in your own words. Check the exact medicine name on its label.</p><div className="suggestions">{suggestions.map(s=><button className="secondary" onClick={()=>void send(s)} key={s}>{s}<ArrowRight size={16}/></button>)}</div>{!suggestions.length&&<p>Approved source topics will appear here when available.</p>}</div>}
        {messages.map((m,index)=><article ref={index===messages.length-1?latest:undefined} key={m.id} className={'message '+m.role} data-message-id={m.id}>
          <span className="message-avatar">{m.role==='assistant'?<HeartPulse size={18}/>:<span>You</span>}</span><div className="message-body"><strong>{m.role==='assistant'?'MediGuide':'You'}</strong><ReactMarkdown components={markdown}>{m.content}</ReactMarkdown>
          {m.response&&<><span className={'evidence-label '+(m.response.citations.length?'':'limited')}><ShieldCheck size={13}/>{m.response.clarification?'Confirm medicine or topic':m.response.evidence_status.replaceAll('_',' ').toLowerCase()}</span>
            {m.response.clarification&&<div className="clarification" role="group" aria-label="Confirm medicine name or question"><strong>{m.response.clarification.kind==='medicine_spelling'?'Check the medicine name on your packet':'Choose a question covered by the references'}</strong>{m.response.clarification.candidates.map(c=><button className="secondary" key={c.medicine} disabled={busy} onClick={()=>void send(c.suggested_query)}>{m.response!.clarification!.kind==='medicine_spelling'?`Confirm ${c.medicine}`:c.suggested_query}<ArrowRight size={14}/></button>)}</div>}
            {m.response.safety_alerts.map((a,i)=><div className="notice warning" key={i}><TriangleAlert size={16}/>{a}</div>)}
            {m.response.citations.length>0&&<div className="citations"><span className="nav-label">SOURCES & EVIDENCE</span>{m.response.citations.map((c,i)=><CitationDetails key={c.chunk_id} citation={c} index={i}/>)}</div>}
            <button className="text-button" onClick={()=>void copy(m)}>{copied===m.id?<Check size={14}/>:<Clipboard size={14}/>} {copied===m.id?'Copied':'Copy answer'}</button>
            <div className="followups">{m.response.follow_up_suggestions.filter(s=>m.response?.diagnostics?.runtime_id||suggestions.includes(s)).map(s=><button disabled={busy} className="text-button" key={s} onClick={()=>void send(s)}>{s}<ArrowRight size={12}/></button>)}</div>
          </>}</div></article>)}
        {busy&&<div className="loading" role="status"><LoaderCircle className="spin" size={18}/> Checking evidence and safety…</div>}
      </div>
      {error&&<div className="notice danger" role="alert"><TriangleAlert size={18}/>{error}</div>}
      <form className="composer" onSubmit={submit}><label className="sr-only" htmlFor="question">Your question</label><textarea id="question" value={query} onChange={e=>setQuery(e.target.value)} placeholder="Ask a health or medication question…" rows={2} maxLength={4000} disabled={busy||loading}/><button aria-label="Send question" disabled={busy||loading||query.trim().length<2}><Send size={18}/></button></form>
      <small className="chat-disclaimer">For education only. Avoid sharing sensitive personal details. For urgent symptoms, seek immediate medical care.</small>
    </section></div></>
}
