// @vitest-environment jsdom
import React from 'react'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import '@testing-library/jest-dom/vitest'
import { MemoryRouter } from 'react-router-dom'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import App from './App'
import { api } from './api'
vi.mock('./api',()=>({api:{get:vi.fn(),post:vi.fn(),patch:vi.fn(),delete:vi.fn()},errorText:()=> 'Service unavailable'}))
describe('Application routes and API integration',()=>{
  beforeEach(()=>{
    vi.resetAllMocks()
    vi.stubGlobal('ResizeObserver',class {observe(){}unobserve(){}disconnect(){}})
  })
  it('shows the education boundary on the landing page',async()=>{
    vi.mocked(api.get).mockRejectedValue(new Error('unauthenticated'))
    render(<MemoryRouter><App/></MemoryRouter>)
    expect(await screen.findByText('A little more clarity.')).toBeInTheDocument()
    expect(screen.getByText(/not clinically validated/)).toBeInTheDocument()
  })
  it('signs in using the backend and renders account activity',async()=>{
    const user={id:'1',name:'Alex',email:'alex@example.test',role:'patient',preferences:{}}
    vi.mocked(api.get).mockImplementation(async(path)=>{
      if(path==='/auth/me')throw new Error('unauthenticated')
      if(String(path).startsWith('/conversations'))return {data:[]}
      return {data:{conversations:0,queries:0,safety_escalations:0,source_status:{approved_documents:0}}}
    })
    vi.mocked(api.post).mockResolvedValue({data:user})
    render(<MemoryRouter initialEntries={['/login']}><App/></MemoryRouter>)
    fireEvent.change(await screen.findByLabelText('Email address'),{target:{value:'alex@example.test'}})
    fireEvent.change(screen.getByLabelText('Password'),{target:{value:'long-password-123'}})
    fireEvent.click(screen.getByRole('button',{name:/^sign in/i}))
    await waitFor(()=>expect(api.post).toHaveBeenCalledWith('/auth/login',{email:'alex@example.test',password:'long-password-123'}))
    expect(await screen.findByText('Hello, Alex.')).toBeInTheDocument()
    expect(screen.queryByText('Knowledge base')).not.toBeInTheDocument()
  })
  it.each([
    ['chat','Your AI education assistant'],['medications','Medication explorer'],['interactions','Interaction checker'],
    ['education','Patient education library'],['knowledge','Knowledge base'],['agents','Agent monitor'],
    ['analytics','Reports & analytics'],['settings','Settings & profile']
  ])('renders the %s screen with connected API data',async(route,title)=>{
    const user={id:'admin',name:'Test admin',email:'admin@example.test',role:'admin',preferences:{}}
    vi.mocked(api.get).mockImplementation(async(path)=>{
      if(path==='/auth/me')return {data:user}
      if(path==='/analytics/overview')return {data:{conversations:0,queries:0,query_categories:{},evidence_statuses:{},retrieval_success_rate:null,citation_validation_rate:null,insufficient_evidence_rate:null,safety_escalations:0,source_status:{approved_documents:0}}}
      return {data:[]}
    })
    const view=render(<MemoryRouter initialEntries={['/app/'+route]}><App/></MemoryRouter>)
    expect(await screen.findByRole('heading',{level:1,name:title})).toBeInTheDocument()
    view.unmount()
  })
})
