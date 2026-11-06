from app.agents.orchestrator import run
from app.agents.response_generation import ABSTENTION
from app.rag.query import query_variants,resolve_query,section_topic
from test_rag_regressions import medicine_source

def test_refusal_echo_never_becomes_medical_evidence(patient,db):
    medicine_source(db)
    for text in [ABSTENTION,ABSTENTION+' paracetamol']:
        response=patient.post('/api/chat',json={'query':text}).json()
        assert response['evidence_status']=='INSUFFICIENT_EVIDENCE'
        assert not response['citations'] and not response.get('clarification')
        assert response['diagnostics']['query_variants']==[]
        assert 'send the original' in response['answer']

def test_rewrite_preserves_exact_identity_and_original_question(db):
    medicine_source(db)
    q='What unwanted reactions can paracetamol cause?'
    variants=query_variants(db,q)
    assert variants[0]==q and len(variants)==2
    assert 'paracetamol' in variants[1] and 'side effects' in variants[1]
    assert resolve_query(db,'What about its side effects?',ABSTENTION+' paracetamol')=='What about its side effects?'
    assert query_variants(db,'side effects of FictionalDrugQ')==['side effects of FictionalDrugQ']

def test_missing_leaflet_source_does_not_borrow_a_medicine_uses_passage(db):
    medicine_source(db)
    result=run(db,'How can I understand my medication leaflet?')
    assert result['evidence_status']=='INSUFFICIENT_EVIDENCE' and not result['citations']

def test_specific_missing_evidence_is_not_a_safety_assurance(db):
    medicine_source(db)
    result=run(db,'Does paracetamol interact with FictionalDrugQ?')
    assert not result['citations'] and result['validation']=='passed'
    assert 'does not establish' in result['answer']

def test_faq_interaction_and_missed_dose_sections_are_recognized():
    assert section_topic('Can I take it with painkillers?')=='interactions'
    assert section_topic('If you forget to take it')=='missed_dose'

def test_new_unknown_question_does_not_inherit_old_medicine(db):
    medicine_source(db)
    q='What precautions should I take with FictionalDrugQ?'
    assert resolve_query(db,q,'What is paracetamol used for?')==q
    result=run(db,q,'What is paracetamol used for?')
    assert not result['citations'] and 'approved reference' in result['answer']
    assert not run(db,result['answer'])['citations']
    assert not run(db,'Can paracetamol and FictionalDrugQ interact?')['citations']
