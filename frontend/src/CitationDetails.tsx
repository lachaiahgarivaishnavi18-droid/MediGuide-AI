import type { Citation } from './types'

export default function CitationDetails({citation:c,index}:{citation:Citation;index:number}) {
  return <details><summary>[{index+1}] {c.title} <span>{c.source_name}</span></summary><p>{c.excerpt}</p>
    <small>Section: {c.section} · Passage: {c.chunk_id}</small>
    {c.attribution&&<small>{c.attribution}</small>}
    {c.population_scope&&<small>Scope: {c.population_scope}</small>}
    {c.retrieved_at&&<small>Source retrieved: {c.retrieved_at.slice(0,10)}</small>}
    {c.source_updated_at&&<small>Source updated: {c.source_updated_at}</small>}
    {c.url&&<a href={c.url} target="_blank" rel="noreferrer">Open original source ↗</a>}
    {c.license_url&&<a href={c.license_url} target="_blank" rel="noreferrer">Source licence ↗</a>}
  </details>
}
