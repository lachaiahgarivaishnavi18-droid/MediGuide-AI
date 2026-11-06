"""Exercise the local frontend proxy and API with a temporary synthetic account."""
import argparse
import sys
import uuid
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'backend'))
import httpx
from sqlalchemy import select
from app.database.session import SessionLocal
from app.models.models import User, Conversation

parser=argparse.ArgumentParser()
parser.add_argument('--url',default='http://127.0.0.1:5173')
args=parser.parse_args()
email=f'smoke-{uuid.uuid4().hex}@example.test'
try:
    with httpx.Client(base_url=args.url,timeout=60,headers={"Origin":args.url}) as client:
        response=client.get('/');response.raise_for_status();assert 'MediGuide' in response.text
        response=client.get('/health');response.raise_for_status();assert response.json()['status']=='ok'
        response=client.post('/api/auth/register',json={'email':email,'name':'Synthetic smoke test','password':uuid.uuid4().hex})
        response.raise_for_status();assert response.json()['role']=='patient'
        response=client.get('/api/knowledge/status');response.raise_for_status()
        assert response.json()['approved_chunks']>0,'No approved evidence: run scripts/import_trusted_references.py before testing medical chat'
        response=client.post('/api/chat',json={'query':'What are the common side effects of Paracetamol?'})
        response.raise_for_status();grounded=response.json()
        assert grounded['evidence_status']=='LIMITED_EVIDENCE' and grounded['citations']
        assert all(c['excerpt'] in grounded['answer'] and c['url'].startswith('https://') for c in grounded['citations'])
        response=client.post('/api/chat',json={'query':'What are the side effects of FictionalDrugQ?','conversation_id':grounded['conversation_id']})
        response.raise_for_status();assert response.json()['evidence_status']=='INSUFFICIENT_EVIDENCE' and not response.json()['citations']
        response=client.post('/api/chat',json={'query':'I cannot breathe'})
        response.raise_for_status();answer=response.json();assert answer['safety_status']=='URGENT_ESCALATION'
        response=client.get('/api/chat/'+answer['conversation_id']+'/messages')
        response.raise_for_status();assert len(response.json())==2
        response=client.post('/api/interactions/check',json={'medications':['Synthetic unknown A','Synthetic unknown B']})
        response.raise_for_status();assert response.json()['status']=='NEEDS_PROFESSIONAL_REVIEW'
        assert client.get('/api/knowledge/documents').status_code==403
        response=client.delete('/api/conversations/'+answer['conversation_id']);assert response.status_code==204
        response=client.post('/api/auth/logout');assert response.status_code==204
        assert client.get('/api/auth/me').status_code==401
    print('PASS: frontend, proxy, health, registration, session, real medical retrieval/citations, unknown-medicine abstention, emergency chat, history, interaction uncertainty, RBAC, deletion, logout')
finally:
    # Only this run's generated synthetic account is removed. Never touch real accounts.
    with SessionLocal() as db:
        user=db.scalar(select(User).where(User.email==email))
        if user:
            db.delete(user);db.commit()
