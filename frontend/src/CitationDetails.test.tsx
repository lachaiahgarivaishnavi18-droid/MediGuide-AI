// @vitest-environment jsdom
import React from 'react'
import { render,screen } from '@testing-library/react'
import '@testing-library/jest-dom/vitest'
import { it,expect } from 'vitest'
import CitationDetails from './CitationDetails'

it('shows the supporting passage with original source, date, scope, and licence',()=>{
  render(<CitationDetails index={0} citation={{document_id:'doc',chunk_id:'chunk',title:'Official reference',source_name:'NHS',url:'https://www.nhs.uk/medicines/paracetamol-for-adults/',section:'Side effects',excerpt:'Exact approved reference passage.',retrieved_at:'2026-11-06T00:00:00Z',population_scope:'Adults; England',attribution:'Information from the NHS website.',license_url:'https://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/'}}/>)
  expect(screen.getByText('Exact approved reference passage.')).toBeInTheDocument()
  expect(screen.getByText('Source retrieved: 2026-11-06')).toBeInTheDocument()
  expect(screen.getByText('Scope: Adults; England')).toBeInTheDocument()
  expect(screen.getByRole('link',{name:/Open original source/,hidden:true})).toHaveAttribute('href','https://www.nhs.uk/medicines/paracetamol-for-adults/')
})
