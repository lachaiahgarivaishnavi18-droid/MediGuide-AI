"""Reproducible local-corpus regression checks; no clinical performance claim."""
import argparse
import json
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'backend'))
from app.database.session import SessionLocal
from app.agents.orchestrator import run
from app.rag.diagnostics import diagnose,corpus_status

CASES=[
    ('What are the common side effects of Paracetamol?','LIMITED_EVIDENCE','side effects','NHS'),
    ('What is paracetamol used for?','LIMITED_EVIDENCE','for','NHS'),
    ('What is Paracetamol?','LIMITED_EVIDENCE','for','NHS'),
    ('How should paracetamol be stored?','LIMITED_EVIDENCE','store','HPRA'),
    ('What are the common side effects of ibuprofen?','LIMITED_EVIDENCE','side effects','NHS'),
    ('What is ibuprofen used for?','LIMITED_EVIDENCE','for','NHS'),
    ('Tell me about ibuprofen.','LIMITED_EVIDENCE','for','NHS'),
    ('What are the side effects of Panadol?','LIMITED_EVIDENCE','side effects','NHS'),
    ('What are the common side effects of amoxicillin?','LIMITED_EVIDENCE','side effects','NHS'),
    ('What are common side effects of FictionalDrugQ?','INSUFFICIENT_EVIDENCE',None,None),
    ('How should ibuprofen be stored?','INSUFFICIENT_EVIDENCE',None,None),
]


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,default=Path('runtime/rag-diagnostics.json'));args=parser.parse_args()
    cases=[]
    with SessionLocal() as db:
        status=corpus_status(db)
        for query,expected,section,source in CASES:
            state=run(db,query)
            citations=state['citations']
            passed=state['evidence_status']==expected and state['validation']=='passed'
            if expected=='LIMITED_EVIDENCE':
                passed=passed and bool(citations) and all(section in e['section'].lower() for e in citations) and source in citations[0]['source_name']
            else:passed=passed and not citations
            cases.append({'query':query,'passed':bool(passed),'evidence_status':state['evidence_status'],'validation':state['validation'],
                          'citations':[{key:e.get(key) for key in ('document_id','chunk_id','source_name','url','section','bm25_score','vector_score','rrf_score')} for e in citations]})
        for query,context,expected in [
            ('What about its side effects?','What is paracetamol used for?','LIMITED_EVIDENCE'),
            ('What are common side effects of amoxicillin?','What are paracetamol side effects?','LIMITED_EVIDENCE')]:
            state=run(db,query,context)
            cases.append({'query':query,'context':context,'passed':state['evidence_status']==expected,'evidence_status':state['evidence_status']})
        for query,status_expected in [('Should I double my paracetamol dose?','NEEDS_PROFESSIONAL_REVIEW'),('I cannot breathe after taking paracetamol','URGENT_ESCALATION')]:
            state=run(db,query)
            cases.append({'query':query,'passed':state['safety_status']==status_expected and not state['citations'],'safety_status':state['safety_status']})
        report={'clinical_validation':False,'corpus':status,'embedding_check':diagnose(db,CASES[0][0])['query_embedding'],'results':cases}
    args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps({'passed':sum(c['passed'] for c in cases),'total':len(cases),'report':str(args.output)}))
    if not all(c['passed'] for c in cases):raise SystemExit(1)


if __name__=='__main__':main()
