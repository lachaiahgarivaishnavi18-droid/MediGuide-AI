"""End-to-end HTTP checks against the public frontend and its proxied backend."""
import argparse,json,secrets,uuid
from pathlib import Path
import httpx

QUESTIONS=[
'What are the common side effects of paracetamol?',
'What is ibuprofen used for?',
'How can I understand my medication leaflet?',
'What are the side effects of cetirizine?',
'Can paracetamol and cetirizine interact?',
'What precautions should I take when using amoxicillin?',
'What is metformin used for?']

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--url',required=True);args=parser.parse_args()
    origin=args.url.rstrip('/')
    if not origin.startswith('https://'):raise SystemExit('Use the deployed HTTPS frontend origin.')
    destination=Path('runtime/deployed-app-results.json');results=[]
    email=f'e2e-{uuid.uuid4()}@example.test';password=secrets.token_urlsafe(32)
    with httpx.Client(base_url=origin,headers={'Origin':origin},timeout=120) as client:
        response=client.get('/api/system/status');response.raise_for_status();runtime=response.json()
        response=client.post('/api/auth/register',json={'email':email,'name':'Deployment verification','password':password})
        if response.status_code!=201:raise SystemExit(f'Test registration failed: HTTP {response.status_code}; credentials not logged.')
        credentials=Path('runtime/cloud-test-credentials.json')
        credentials.write_text(json.dumps({'email':email,'password':password}),encoding='utf-8')
        assert client.get('/api/auth/me').status_code==200
        corpus=client.get('/api/knowledge/status').json();conversation=None
        cases=[(q,'LIMITED_EVIDENCE') for q in QUESTIONS]+[
            ('What are the side effects of FictionalDrugQ?','INSUFFICIENT_EVIDENCE'),
            ('I could not find sufficient approved evidence in this knowledge base to answer reliably. Please consult the official patient leaflet or a pharmacist or qualified healthcare professional.','INSUFFICIENT_EVIDENCE'),
            ('I cannot breathe after taking paracetamol','INSUFFICIENT_EVIDENCE')]
        for question,expected in cases:
            response=client.post('/api/chat',json={'query':question,**({'conversation_id':conversation} if conversation else {})})
            body=response.json();conversation=body.get('conversation_id',conversation)
            passed=response.status_code==200 and body.get('evidence_status')==expected
            citations=body.get('citations',[])
            if expected=='LIMITED_EVIDENCE':
                passed=passed and bool(citations) and body.get('diagnostics',{}).get('citation_validation')=='passed'
                passed=passed and all(c.get('supporting_quotes') and all(q in c['excerpt'] and q in body['answer'] for q in c['supporting_quotes']) for c in citations)
            else:passed=passed and not citations
            if question.startswith('I cannot breathe'):passed=passed and body.get('safety_status')=='URGENT_ESCALATION'
            results.append({'question':question,'http_status':response.status_code,'passed':bool(passed),'response':body})
            print(('PASS ' if passed else 'FAIL ')+question,flush=True)
        if conversation:client.delete('/api/conversations/'+conversation)
        client.post('/api/auth/logout')
    report={'url':origin,'runtime':runtime,'corpus':corpus,'passed':sum(r['passed'] for r in results),'total':len(results),'results':results,
            'note':'Synthetic test account retained for browser verification. Test conversation removed. No administrator credentials used.'}
    destination.write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps({'passed':report['passed'],'total':report['total']}))
    return 0 if all(r['passed'] for r in results) else 1

if __name__=='__main__':raise SystemExit(main())
