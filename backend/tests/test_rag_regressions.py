from datetime import datetime,timedelta,timezone
from io import BytesIO
import numpy as np
import pytest
from sqlalchemy import select
from app.knowledge_base.ingestion import ingest,extract,chunk_text
from app.knowledge_base.references import REFERENCES,parse_reference,download_reference
from app.schemas.api import IngestRequest
from app.models.models import KnowledgeChunk
from app.rag.retrieval import retrieve,embed,indexed_corpus
from app.rag.query import resolve_query
from app.agents.orchestrator import run
from app.agents.citation_validation import run as validate
from app.agents.response_generation import render
from app.rag.diagnostics import diagnose


def medicine_source(db,name='paracetamol',approved=True,synthetic=False):
    # Brief real NHS statement; an isolated fixture, not a fictional medical fact.
    statement='Paracetamol very rarely causes side effects if you take it correctly.' if name=='paracetamol' else 'Like all medicines, ibuprofen can cause side effects, although not everyone gets them.'
    text=f'# {name.title()} reference\n\n# What {name} is for\n\nSee the official medicine reference for indications.\n\n# Side effects of {name}\n\n{statement}\n\n# How to store {name}\n\nConsult the product-specific leaflet for storage instructions.'
    doc,_=ingest(db,IngestRequest(title=f'{name.title()} reference',source_name='NHS fixture',source_url=f'https://www.nhs.uk/medicines/{name}-for-adults/',text=text,approved=approved,synthetic=synthetic,metadata={'medications':[name]}))
    db.commit()
    return doc


def test_section_boundaries_and_warning_context():
    text='# Purpose\n\nPurpose content must remain here.\n\n# Side effects\n\nRare effects context.\n\n'+('warning '*400)+'\n\n# Storage\n\nStore only according to the product label.'
    chunks=chunk_text(text)
    assert [s for s,_ in chunks]==['Purpose','Side effects','Storage']
    assert 'Purpose content' not in chunks[1][1]
    assert 'Rare effects context' in chunks[1][1] and chunks[1][1].count('warning')==400
    assert 'warning' not in chunks[2][1]


def test_retrieve_medicine_topic_without_unrelated_sections(db):
    medicine_source(db);medicine_source(db,'ibuprofen')
    found=retrieve(db,'What are the common side effects of Paracetamol?')
    assert found and all(e['section']=='Side effects of paracetamol' for e in found)
    assert all(e['matched_medications']==['paracetamol'] for e in found)
    assert all(e['matched_topic']=='side_effects' for e in found)
    assert all(e['bm25_score']>0 for e in found)
    assert 'very rarely' in found[0]['excerpt']
    assert retrieve(db,'What are the side effects of Amoxicillin?')==[]
    assert retrieve(db,'Does FictionalDrugQ cause side effects?')==[]
    assert retrieve(db,'What are side effects of paracetamol and FictionalDrugQ?')==[]


def test_context_does_not_contaminate_new_medicine(db):
    medicine_source(db);medicine_source(db,'ibuprofen')
    old='What are the common side effects of Paracetamol?'
    new='What are the side effects of amoxicillin?'
    assert resolve_query(db,new,old)==new
    assert run(db,new,old)['evidence_status']=='INSUFFICIENT_EVIDENCE'
    assert run(db,'What about its side effects?',old+'\nWhat is amoxicillin?')['evidence_status']=='INSUFFICIENT_EVIDENCE'
    follow=run(db,'What about its side effects?','What is paracetamol used for?')
    assert follow['citations'] and all('paracetamol' in e['section'] for e in follow['citations'])
    switch=run(db,'What are ibuprofen side effects?',old)
    assert switch['citations'] and all('ibuprofen' in e['section'] for e in switch['citations'])


def test_approval_expiry_and_embedding_cache(db):
    doc=medicine_source(db)
    indexed_corpus.cache_clear()
    first=retrieve(db,'Paracetamol side effects')
    assert first
    misses=indexed_corpus.cache_info().misses
    retrieve(db,'Paracetamol side effects')
    assert indexed_corpus.cache_info().misses==misses and indexed_corpus.cache_info().hits>0
    vector=embed(['Paracetamol side effects'])
    assert vector.shape==(1,512) and np.linalg.norm(vector[0])==pytest.approx(1)
    doc.approved=False;db.commit()
    assert not retrieve(db,'Paracetamol side effects')
    doc.approved=True;doc.metadata_json={**doc.metadata_json,'expires_at':(datetime.now(timezone.utc)-timedelta(days=1)).isoformat()};db.commit()
    assert not retrieve(db,'Paracetamol side effects')
    assert diagnose(db,'Paracetamol side effects')['corpus']['expired_documents']==1


def test_forged_citation_source_rejected(db):
    medicine_source(db)
    selected=retrieve(db,'paracetamol side effects')
    selected[0]['url']='https://fabricated.example/source'
    assert validate({'db':db,'selected':selected,'answer':render(selected)})['validation']=='rejected'


def test_scanned_empty_pdf_rejected(admin):
    import fitz
    pdf=fitz.open();pdf.new_page();data=pdf.tobytes();pdf.close()
    with pytest.raises(ValueError,match='OCR'):extract(data,'.pdf')
    response=admin.post('/api/knowledge/documents/upload',data={'title':'Scanned empty PDF','source_name':'Test'},files={'file':('scan.pdf',data,'application/pdf')})
    assert response.status_code==422
    assert 'OCR' in response.json()['detail']


def test_uploaded_pdf_medicine_tags_are_source_anchored(admin):
    import fitz
    pdf=fitz.open();page=pdf.new_page();page.insert_text((72,72),'4. POSSIBLE SIDE EFFECTS\nParacetamol very rarely causes side effects if you take it correctly.')
    data=pdf.tobytes();pdf.close()
    base={'title':'Uploaded leaflet reference','source_name':'Isolated test fixture','medications':'paracetamol'}
    response=admin.post('/api/knowledge/documents/upload',data=base,files={'file':('leaflet.pdf',data,'application/pdf')})
    assert response.status_code==201,response.text
    assert admin.post('/api/knowledge/retrieve',json={'query':'paracetamol side effects'}).json()==[]
    admin.patch('/api/knowledge/documents/'+response.json()['id'],json={'approved':True})
    found=admin.post('/api/knowledge/retrieve',json={'query':'paracetamol side effects'}).json()
    assert found and found[0]['matched_medications']==['paracetamol']
    assert admin.post('/api/knowledge/documents/upload',data={**base,'medications':'ibuprofen'},files={'file':('leaflet.pdf',data,'application/pdf')}).status_code==422


def test_pdf_and_docx_upload_to_retrieval(admin):
    import fitz
    text='Reference catalog provenance and section identifiers are retained for review.'
    pdf=fitz.open();page=pdf.new_page();page.insert_text((72,72),text);data=pdf.tobytes();pdf.close()
    response=admin.post('/api/knowledge/documents/upload',data={'title':'Catalog PDF','source_name':'Fixture'},files={'file':('catalog.pdf',data,'application/pdf')})
    assert response.status_code==201
    id=response.json()['id']
    assert admin.patch('/api/knowledge/documents/'+id,json={'approved':True}).status_code==200
    found=admin.post('/api/knowledge/diagnose',json={'query':'catalog provenance'}).json()
    assert found['result_count'] and found['query_embedding']['finite']
    assert found['corpus']['document_types']['.pdf']==1
    from docx import Document
    doc=Document();doc.add_paragraph('DOCX reference catalog retains original provenance and source identifiers.');stream=BytesIO();doc.save(stream)
    response=admin.post('/api/knowledge/documents/upload',data={'title':'Catalog DOCX','source_name':'Fixture'},files={'file':('catalog.docx',stream.getvalue(),'application/vnd.openxmlformats-officedocument.wordprocessingml.document')})
    assert response.status_code==201
    admin.patch('/api/knowledge/documents/'+response.json()['id'],json={'approved':True})
    assert admin.post('/api/knowledge/retrieve',json={'query':'DOCX provenance'}).json()


def test_reference_parser_keeps_nhs_sections_and_provenance():
    html=b'<html><main><h1>Paracetamol for adults - Panadol</h1><section><h2>Side effects of paracetamol</h2><p>Paracetamol very rarely causes side effects if you take it correctly.</p><h3>Serious side effects</h3><p>Consult the original reference.</p></section></main></html>'
    payload=parse_reference(REFERENCES[0],html)
    assert payload.approved and not payload.synthetic
    assert payload.metadata['license_url'] and payload.metadata['retrieved_at']
    chunks=chunk_text(payload.text)
    assert any('Serious side effects' in text and 'very rarely' in text for section,text in chunks)
    with pytest.raises(ValueError):parse_reference(REFERENCES[0],b'<main><h1>Wrong identity</h1></main>')


def test_reference_fetch_respects_robots_and_allowlist():
    import httpx
    transport=httpx.MockTransport(lambda request:httpx.Response(200,text='User-agent: *\nDisallow: /' if request.url.path=='/robots.txt' else 'Not accessed'))
    with httpx.Client(transport=transport) as client:
        with pytest.raises(ValueError,match='disallows'):download_reference(client,REFERENCES[0],{})
        with pytest.raises(ValueError,match='manifest'):download_reference(client,{'url':'https://evil.example'},{})


def test_diagnostics_and_chat_citations(patient,db):
    medicine_source(db)
    assert patient.post('/api/knowledge/diagnose',json={'query':'paracetamol side effects'}).status_code==403
    status=patient.get('/api/knowledge/status').json()
    assert status['index_status']=='ready' and status['approved_chunks']>0
    result=patient.post('/api/chat',json={'query':'What are common side effects of Paracetamol?'}).json()
    assert result['evidence_status']=='LIMITED_EVIDENCE' and result['citations']
    assert result['citations'][0]['supporting_quotes']
    assert all(q in result['answer'] and q in result['citations'][0]['excerpt'] for q in result['citations'][0]['supporting_quotes'])
    follow=patient.post('/api/chat',json={'query':'What are common side effects of amoxicillin?','conversation_id':result['conversation_id']}).json()
    assert follow['evidence_status']=='INSUFFICIENT_EVIDENCE' and not follow['citations']
