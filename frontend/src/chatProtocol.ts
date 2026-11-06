import type { ChatResponse,Message } from './types'

function object(value:unknown):value is Record<string,unknown>{return !!value&&typeof value==='object'}
function strings(value:unknown):value is string[]{return Array.isArray(value)&&value.every(s=>typeof s==='string')}

export function parseChatResponse(value:unknown):ChatResponse{
  if(!object(value)||!['conversation_id','message_id','answer','intent','evidence_status','safety_status'].every(key=>typeof value[key]==='string')||
    !Array.isArray(value.citations)||!value.citations.every(c=>object(c)&&['document_id','chunk_id','source_name','title','url','section','excerpt'].every(key=>typeof c[key]==='string'))||
    !strings(value.safety_alerts)||!strings(value.follow_up_suggestions)||!strings(value.limitations))throw new Error('The server returned an invalid chat response. Please try again; no replacement answer was generated.')
  if(!['HIGH_CONFIDENCE_EVIDENCE','LIMITED_EVIDENCE','CONFLICTING_EVIDENCE','INSUFFICIENT_EVIDENCE','SOURCE_UNAVAILABLE'].includes(String(value.evidence_status)))throw new Error('The server returned an invalid evidence status.')
  if(value.clarification!=null&&(!object(value.clarification)||!['medicine_spelling','medicine_required'].includes(String(value.clarification.kind))||!Array.isArray(value.clarification.candidates)||!value.clarification.candidates.every(c=>object(c)&&typeof c.medicine==='string'&&typeof c.suggested_query==='string')))throw new Error('The server returned an invalid medicine-name clarification.')
  return value as unknown as ChatResponse
}

export function parseMessages(value:unknown):Message[]{
  if(!Array.isArray(value))throw new Error('The server returned invalid conversation history.')
  return value.map(m=>{
    if(!object(m)||typeof m.id!=='string'||!['user','assistant'].includes(String(m.role))||typeof m.content!=='string')throw new Error('The server returned an invalid conversation message.')
    const response=m.response==null?undefined:parseChatResponse(m.response)
    return {id:m.id,role:String(m.role),content:response?.answer??m.content,response}
  })
}
