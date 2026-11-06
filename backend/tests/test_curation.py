from app.models.models import KnowledgeChunk
from sqlalchemy import select

TEXT = '# Synthetic test label (software fixture, no clinical facts)\n\nTest compound A and Test compound B contain Test ingredient. Both names appear here for software testing only.\n\nStorage: this fictional catalog contains no medical storage guidance.'


def test_structured_curation_gates(admin,db):
    doc=admin.post('/api/knowledge/documents/ingest',json={'title':'Synthetic test label','source_name':'Test fixture','text':TEXT,'approved':True}).json()
    chunk=db.scalar(select(KnowledgeChunk).where(KnowledgeChunk.document_id==doc['id']))
    payload={'document_id':doc['id'],'generic_name':'Test compound A','active_ingredients':['Test ingredient'],'facts':[{'field':'storage','text':'this fictional catalog contains no medical storage guidance.','chunk_id':chunk.id}]}
    response=admin.post('/api/admin/medications',json=payload)
    assert response.status_code==201,response.text
    aid=response.json()['id']
    bid=admin.post('/api/admin/medications',json={**payload,'generic_name':'Test compound B'}).json()['id']
    assert admin.get('/api/medications/search?q=Test%20ingredient').json()
    assert admin.get('/api/medications/'+aid).json()['active_ingredients']==['test ingredient']
    assert admin.post('/api/admin/medications',json={**payload,'generic_name':'Invented name'}).status_code==422
    assert admin.post('/api/admin/medications',json={**payload,'facts':[{'field':'warnings','text':'Fabricated medical warning','chunk_id':chunk.id}]}).status_code==422
    record=admin.post('/api/admin/interactions',json={'medication_a':aid,'medication_b':bid,'chunk_id':chunk.id,'text':'Both names appear here for software testing only.'})
    assert record.status_code==201,record.text
    result=admin.post('/api/interactions/check',json={'medications':['Test compound A','Test compound B']}).json()
    assert result['findings'] and result['duplicate_ingredients']
    assert result['status']=='NEEDS_PROFESSIONAL_REVIEW'
    topic=admin.post('/api/admin/education',json={'document_id':doc['id'],'category':'general'})
    assert topic.status_code==201
    assert admin.get('/api/education/'+topic.json()['id']).json()['document']['id']==doc['id']
    assert admin.patch('/api/knowledge/documents/'+doc['id'],json={'approved':False}).status_code==200
    assert admin.get('/api/medications/'+aid).status_code==404
    assert not admin.post('/api/interactions/check',json={'medications':['Test compound A','Test compound B']}).json()['findings']
