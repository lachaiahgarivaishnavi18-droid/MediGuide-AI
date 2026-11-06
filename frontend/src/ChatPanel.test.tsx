// @vitest-environment jsdom
import React from 'react'
import { describe,it,expect,vi,beforeEach,afterEach } from 'vitest'
import { cleanup,render,screen,fireEvent,waitFor } from '@testing-library/react'
import '@testing-library/jest-dom/vitest'
import { MemoryRouter } from 'react-router-dom'
import ChatPanel from './ChatPanel'
import { api } from './api'
import type {ChatResponse} from './types'
vi.mock('./api',async()=>({...(await vi.importActual<typeof import('./api')>('./api')),api:{get:vi.fn(),post:vi.fn(),delete:vi.fn()}}))
const user={id:'patient',name:'Test user',email:'test@example.test',role:'patient' as const,preferences:{}}
const answer:ChatResponse={conversation_id:'conversation',message_id:'answer',answer:'Approved reference passage [1].',intent:'medication_information',evidence_status:'LIMITED_EVIDENCE',safety_status:'NO_ADDITIONAL_ALERT',citations:[{document_id:'doc',chunk_id:'chunk',title:'Reference',source_name:'Fixture',url:'https://example.test/reference',section:'Purpose',excerpt:'Approved reference passage'}],safety_alerts:[],follow_up_suggestions:[],limitations:[]}
function mount(path='/app/chat'){return render(<MemoryRouter initialEntries={[path]}><ChatPanel user={user}/></MemoryRouter>)}
describe('actual chat response handling',()=>{
  beforeEach(()=>{
    vi.resetAllMocks()
    Object.defineProperty(HTMLElement.prototype,'scrollIntoView',{configurable:true,value:vi.fn()})
    vi.mocked(api.get).mockImplementation(async(path)=>({data:path==='/knowledge/status'?{available_documents:1,approved_chunks:1}:path==='/chat/suggestions'?['What is paracetamol used for?']:[]}))
  })
  afterEach(cleanup)
  it('renders the POST answer directly and does not refetch a stale message snapshot',async()=>{
    vi.mocked(api.post).mockResolvedValue({data:answer})
    mount()
    fireEvent.change(screen.getByLabelText('Your question'),{target:{value:'What is paracetamol used for?'}})
    fireEvent.click(screen.getByRole('button',{name:'Send question'}))
    expect(await screen.findByText(answer.answer)).toBeInTheDocument()
    expect(screen.getByText('limited evidence')).toBeInTheDocument()
    expect(api.get).not.toHaveBeenCalledWith('/chat/conversation/messages',expect.anything())
    await waitFor(()=>expect(HTMLElement.prototype.scrollIntoView).toHaveBeenCalled())
  })
  it('requires an explicit click before sending a proposed medicine spelling',async()=>{
    vi.mocked(api.post).mockResolvedValueOnce({data:{...answer,message_id:'clarify',answer:'Please confirm the medicine name.',evidence_status:'INSUFFICIENT_EVIDENCE',citations:[],clarification:{kind:'medicine_spelling',input_name:'paracetemol',candidates:[{medicine:'paracetamol',suggested_query:'side effects of paracetamol'}]}}}).mockResolvedValueOnce({data:answer})
    mount()
    fireEvent.change(screen.getByLabelText('Your question'),{target:{value:'side effects of paracetemol'}})
    fireEvent.click(screen.getByRole('button',{name:'Send question'}))
    const confirm=await screen.findByRole('button',{name:'Confirm paracetamol'})
    expect(api.post).toHaveBeenCalledTimes(1)
    fireEvent.click(confirm)
    expect(await screen.findByText(answer.answer)).toBeInTheDocument()
    expect(api.post).toHaveBeenLastCalledWith('/chat',{query:'side effects of paracetamol',conversation_id:'conversation'})
  })
  it('reports malformed API data instead of inventing an insufficient-evidence response',async()=>{
    vi.mocked(api.post).mockResolvedValue({data:{answer:'Invalid payload'}})
    mount()
    fireEvent.change(screen.getByLabelText('Your question'),{target:{value:'A source question'}})
    fireEvent.click(screen.getByRole('button',{name:'Send question'}))
    expect(await screen.findByRole('alert')).toHaveTextContent('invalid chat response')
    expect(screen.queryByText('insufficient evidence')).not.toBeInTheDocument()
  })
  it('ignores an old history request that completes after switching conversations',async()=>{
    let finishOld!:(value:unknown)=>void
    const old=new Promise(resolve=>{finishOld=resolve})
    vi.mocked(api.get).mockImplementation(async(path)=>{
      if(path==='/conversations')return {data:[{id:'old',title:'Old conversation'},{id:'new',title:'New selected conversation'}]}
      if(path==='/chat/old/messages')return await old as never
      if(path==='/chat/new/messages')return {data:[{id:'answer',role:'assistant',content:answer.answer,response:answer}]}
      return {data:[]}
    })
    mount('/app/chat?conversation=old')
    fireEvent.click(await screen.findByRole('button',{name:'New selected conversation'}))
    expect(await screen.findByText(answer.answer)).toBeInTheDocument()
    finishOld({data:[{id:'old-answer',role:'assistant',content:'Old insufficient-evidence response'}]})
    await waitFor(()=>expect(screen.queryByText('Old insufficient-evidence response')).not.toBeInTheDocument())
    expect(screen.getByText(answer.answer)).toBeInTheDocument()
  })
})
