"""Software relevance checks on the real approved corpus, not clinical labels."""
import sys,json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'backend'))
from app.database.session import SessionLocal
from app.rag.query import query_variants
from app.rag.retrieval import retrieve
from app.core.config import settings
from app.rag.diagnostics import corpus_status

POSITIVES=[
'What are the common side effects of paracetamol?','What is ibuprofen used for?',
'How can I understand my medication leaflet?','What are the side effects of cetirizine?',
'Can paracetamol and cetirizine interact?','What precautions should I take when using amoxicillin?',
'What is metformin used for?','What unwanted reactions can cetirizine cause?',
'What does metformin help with?','What if I forget to take amoxicillin?',
*[f'What is {medicine} used for?' for medicine in ['azithromycin','pantoprazole','aspirin','vitamin D','vitamin B12','amlodipine','ramipril','omeprazole']],
'What are the serious side effects of azithromycin?','When should ramipril not be used?']
NEGATIVES=['What are the side effects of FictionalDrugQ?','What precautions should I take with FictionalDrugQ?',
'Can cetirizine and FictionalDrugQ interact?','Explain quantum gravity and black holes.',
'I could not find sufficient approved evidence in this knowledge base to answer reliably. Please consult the official patient leaflet or a pharmacist or qualified healthcare professional.']

def main():
    results=[]
    with SessionLocal() as db:
        corpus=corpus_status(db)
        for expected,questions in [(True,POSITIVES),(False,NEGATIVES)]:
            for query in questions:
                found=retrieve(db,query)
                results.append({'query':query,'expected_retrieval':expected,'passed':bool(found)==expected,'variants':query_variants(db,query),
                                'best_vector_score':max((e['vector_score'] for e in found),default=None),
                                'sections':[e['section'] for e in found], 'source_urls':list(dict.fromkeys(e['url'] for e in found))})
    report={'threshold':settings.semantic_min_score,'threshold_changed':False,'clinical_validation':False,'corpus':corpus,'passed':sum(r['passed'] for r in results),'total':len(results),'results':results}
    Path('runtime/retrieval-calibration.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps({k:report[k] for k in ['threshold','passed','total']}))
    for r in results:
        if not r['passed']:print('FAIL',r['query'])
    return 0 if all(r['passed'] for r in results) else 1
if __name__=='__main__':raise SystemExit(main())
