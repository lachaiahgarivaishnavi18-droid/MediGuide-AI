from pathlib import Path
from sqlalchemy.engine import make_url
import pytest
from app.agents.orchestrator import run
from app.agents.citation_validation import run as validate
from app.core.config import Settings,PROJECT_ROOT
from app.services.chat_guidance import available_questions
from app.rag.diagnostics import corpus_status
from test_rag_regressions import medicine_source


@pytest.mark.parametrize('name',['paracetomal','pharacetemol','paracetemol'])
def test_actual_user_spellings_require_confirmation_then_retrieve(db,name):
    medicine_source(db)
    query=f'what are the side effects of {name}'
    first=run(db,query)
    assert first['clarification']['kind']=='medicine_spelling'
    assert first['validation']=='passed' and first['evidence']==[] and first['citations']==[]
    candidate=next(c for c in first['clarification']['candidates'] if c['medicine']=='paracetamol')
    assert name not in candidate['suggested_query'] and 'paracetamol' in candidate['suggested_query']
    confirmed=run(db,candidate['suggested_query'])
    assert confirmed['evidence_status']=='LIMITED_EVIDENCE' and confirmed['validation']=='passed'
    assert confirmed['citations'][0]['supporting_quotes']
    assert all(q in confirmed['answer'] and q in confirmed['citations'][0]['excerpt'] for q in confirmed['citations'][0]['supporting_quotes'])


@pytest.mark.parametrize('query',['What should I ask my pharmacist?','What information is available about medication storage?'])
def test_previous_dead_starter_questions_are_actionable(db,query):
    medicine_source(db)
    state=run(db,query)
    assert state['clarification']['kind']=='medicine_required' and state['validation']=='passed'
    assert not state['citations']
    for candidate in state['clarification']['candidates']:
        assert run(db,candidate['suggested_query'])['citations']


def test_api_response_and_source_derived_followups(patient,db):
    medicine_source(db)
    starters=patient.get('/api/chat/suggestions').json()
    assert starters and 'What should I ask my pharmacist?' not in starters
    first=patient.post('/api/chat',json={'query':'  what are side effects of paracetemol\n'}).json()
    assert first['clarification'] and not first['citations']
    candidate=first['clarification']['candidates'][0]
    response=patient.post('/api/chat',json={'query':candidate['suggested_query'],'conversation_id':first['conversation_id']})
    assert response.status_code==200,response.text
    data=response.json()
    assert data['evidence_status']=='LIMITED_EVIDENCE' and data['diagnostics']['retrieved_passages']>0
    assert data['diagnostics']['citation_validation']=='passed'
    assert data['diagnostics']['corpus_fingerprint']==corpus_status(db)['corpus_fingerprint']
    assert data['diagnostics']['runtime_id']==patient.get('/api/system/status').json()['runtime_id']
    stored=patient.get('/api/chat/'+data['conversation_id']+'/messages').json()[-1]
    assert stored['content']==data['answer']==stored['response']['answer']
    for question in data['follow_up_suggestions']:
        answer=patient.post('/api/chat',json={'query':question,'conversation_id':data['conversation_id']}).json()
        assert answer['citations']


def test_clarification_cannot_bypass_grounding_or_emergency_rules(db):
    medicine_source(db)
    first=run(db,'side effects of paracetemol')
    first['db']=db;first['query']='side effects of paracetemol';first['answer']='Take an invented medication dose.'
    assert validate(first)['validation']=='rejected'
    assert run(db,'I cannot breathe after taking paracetemol')['safety_status']=='URGENT_ESCALATION'
    refused=run(db,'Should I double my paracetemol dose?')
    assert refused['safety_status']=='NEEDS_PROFESSIONAL_REVIEW' and not refused.get('clarification')
    assert run(db,'side effects of amoxicillin')['evidence_status']=='INSUFFICIENT_EVIDENCE'
    assert not run(db,'side effects of amoxicillin').get('clarification')


def test_llm_selection_receives_resolved_followup_context(db,monkeypatch):
    medicine_source(db)
    calls=[]
    def select(query,evidence):
        calls.append(query)
        return evidence[:1]
    monkeypatch.setattr('app.agents.patient_education.select_passages',select)
    state=run(db,'What about its side effects?','What is paracetamol used for?')
    assert calls and 'paracetamol' in calls[0] and state['citations']


def test_database_location_is_independent_of_server_working_directory(monkeypatch):
    monkeypatch.chdir(PROJECT_ROOT/'frontend')
    config=Settings(_env_file=None,database_url='sqlite:///./mediguide.db')
    assert Path(make_url(config.database_url).database)==PROJECT_ROOT/'mediguide.db'
    assert Settings(_env_file=None,database_url='sqlite:///:memory:').database_url=='sqlite:///:memory:'
