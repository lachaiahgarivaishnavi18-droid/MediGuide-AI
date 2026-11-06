"""Synthetic software checks, never a clinical performance evaluation."""
import argparse
import csv
import json
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"backend"))
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from app.database.session import Base
from app.models import models
from app.agents.orchestrator import run
from app.evaluation.metrics import ranking_metrics, annotated_metrics

parser=argparse.ArgumentParser()
parser.add_argument('--output',type=Path,default=Path('runtime/evaluation.json'))
parser.add_argument('--ranking-dataset',type=Path,help='JSON cases with query and relevant chunk IDs; evaluates configured database')
parser.add_argument('--annotations',type=Path,help='Expert-labeled cases for claim/citation/entity/conversation/safety metrics')
args=parser.parse_args()
reports=[]
if args.annotations:
    cases=json.loads(args.annotations.read_text(encoding='utf-8'))
    reports=[{'id':'annotated-assessment',**annotated_metrics(cases)}]
elif args.ranking_dataset:
    from app.database.session import SessionLocal
    from app.rag.retrieval import retrieve
    with SessionLocal() as db:
        for case in json.loads(args.ranking_dataset.read_text(encoding='utf-8')):
            found=retrieve(db,case['query'],case.get('k',5))
            reports.append({'id':case['id'],**ranking_metrics([e['chunk_id'] for e in found],case['relevant_chunk_ids'],case.get('k',5))})
else:
    engine=create_engine('sqlite://');Base.metadata.create_all(engine)
    with Session(engine) as db:
        for case in json.loads(Path('data/evaluation/cases.json').read_text(encoding='utf-8')):
            result=run(db,case['query'])
            checks=[]
            if 'expected_safety' in case:checks.append(result['safety_status']==case['expected_safety'])
            if 'expected_evidence' in case:checks.append(result['evidence_status']==case['expected_evidence'])
            reports.append({'id':case['id'],'passed':all(checks),'safety_status':result['safety_status'],'evidence_status':result['evidence_status'],'citation_count':len(result['citations'])})
args.output.parent.mkdir(parents=True,exist_ok=True)
args.output.write_text(json.dumps({'synthetic':True,'clinical_validation':False,'results':reports,'unmeasured':['clinical correctness','readability','claim-level entailment','context recall without annotated data','false reassurance in real patients']},indent=2),encoding='utf-8')
with args.output.with_suffix('.csv').open('w',newline='',encoding='utf-8') as file:
    writer=csv.DictWriter(file,fieldnames=list(reports[0]) if reports else ['id']);writer.writeheader();writer.writerows(reports)
print(f'Exported {len(reports)} synthetic checks to {args.output}')
if any(r.get('passed') is False for r in reports):sys.exit(1)
