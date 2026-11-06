"""Idempotently import the user-requested, fixed official-reference manifest."""
import argparse
import json
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"backend"))
import httpx
from sqlalchemy import select
from app.database.session import SessionLocal
from app.models.models import KnowledgeDocument, KnowledgeChunk, Medication, EducationTopic, AuditLog
from app.knowledge_base.references import REFERENCES, download_reference, parse_reference
from app.knowledge_base.ingestion import ingest,chunk_text
from app.services.curation import MedicationImport, Fact, import_medication
from app.rag.retrieval import retrieve
from app.core.config import settings


def deployment_references():
    # WHO's bounded local-study extracts are not part of a production import.
    return [r for r in REFERENCES if settings.environment!='production' or r['source']!='WHO']


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--output",type=Path,default=Path("runtime/trusted-reference-import.json"))
    parser.add_argument('--verified-cache',action='store_true',help='Use just-verified local downloads from the catalog probe; for controlled setup only')
    args=parser.parse_args()
    references=deployment_references()
    destination=Path("runtime/sources");destination.mkdir(parents=True,exist_ok=True)
    reports,payloads,policies=[],[],{}
    with httpx.Client(timeout=30,follow_redirects=False) as client:
        for spec in references:
            try:
                cache=Path('runtime/sources')/(spec['id']+'.'+spec['format'])
                probe=Path('runtime/catalog-probe')/(spec['id']+'.'+spec['format'])
                if args.verified_cache and (probe.exists() or cache.exists()):
                    item=probe if probe.exists() else cache
                    if __import__('time').time()-item.stat().st_mtime>86400:raise ValueError('Verified download cache older than 24 hours; fetch again')
                    data=item.read_bytes()
                else:data=download_reference(client,spec,policies)
                payload=parse_reference(spec,data)
                (destination/(spec["id"]+"."+spec["format"])).write_bytes(data)
                payloads.append(payload)
                reports.append({"reference":spec["id"],"url":spec["url"],"status":"verified","characters":len(payload.text)})
            except Exception as exc:
                reports.append({"reference":spec["id"],"url":spec["url"],"status":"failed","error":str(exc)})
    args.output.parent.mkdir(parents=True,exist_ok=True)
    if len(payloads)!=len(references):
        args.output.write_text(json.dumps({"committed":False,"sources":reports},indent=2),encoding="utf-8")
        raise SystemExit("Reference import aborted; see report. Existing corpus was preserved.")
    with SessionLocal() as db:
        for payload,report in zip(payloads,reports):
            doc,created=ingest(db,payload)
            doc.title,doc.source_name,doc.source_url=payload.title,payload.source_name,payload.source_url
            previous=doc.metadata_json
            if not created and previous.get('chunker_version')!=3:
                old_chunks=db.scalars(select(KnowledgeChunk).where(KnowledgeChunk.document_id==doc.id)).all()
                ordinal=max((c.ordinal for c in old_chunks),default=-1)+1
                fresh=[]
                for section,text in chunk_text(payload.text,size=180,overlap=30):
                    chunk=KnowledgeChunk(document_id=doc.id,ordinal=ordinal,section=section,text=text);ordinal+=1;db.add(chunk);db.flush();fresh.append(chunk.id)
                payload.metadata['active_chunk_ids']=fresh
            elif previous.get('active_chunk_ids'):
                payload.metadata['active_chunk_ids']=previous['active_chunk_ids']
            doc.metadata_json={**payload.metadata,"index_version":3}
            doc.approved=True
            if not created:doc.version+=1
            db.flush()
            # Withdraw only superseded versions of this exact manifest source.
            for old in db.scalars(select(KnowledgeDocument).where(KnowledgeDocument.id!=doc.id)):
                if old.source_url==doc.source_url or old.metadata_json.get('reference_id')==payload.metadata['reference_id']:
                    old.approved=False
            chunks=db.scalars(select(KnowledgeChunk).where(KnowledgeChunk.document_id==doc.id)).all()
            if not chunks:raise ValueError("Import produced no chunks")
            active=doc.metadata_json.get('active_chunk_ids')
            chunks=[c for c in chunks if active is None or c.id in active]
            report.update({"document_id":doc.id,"created":created,"chunks":len(chunks),"approved":True})
            if payload.metadata.get('medications') and (payload.metadata['reference_id'] in {'nhs-paracetamol','nhs-ibuprofen'} or next((r.get('primary') for r in REFERENCES if r['id']==payload.metadata['reference_id']),False)) and not db.scalar(select(Medication).where(Medication.document_id==doc.id)):
                facts=[]
                for chunk in chunks:
                    if chunk.section.lower().startswith("side effects"):
                        facts.append(Fact(field="side_effects",text=chunk.text,chunk_id=chunk.id))
                    elif chunk.section.lower().startswith("what "):
                        facts.append(Fact(field="purpose",text=chunk.text,chunk_id=chunk.id))
                import_medication(db,MedicationImport(document_id=doc.id,generic_name=payload.metadata["medications"][0],brand_names=list(payload.metadata["medication_aliases"]),active_ingredients=payload.metadata["medications"],facts=facts),None)
            if not db.scalar(select(EducationTopic).where(EducationTopic.document_id==doc.id)):
                db.add(EducationTopic(title=doc.title,category='medication' if payload.metadata.get('medications') else 'general',document_id=doc.id))
            db.add(AuditLog(action="trusted_reference_verified",resource_id=doc.id))
        db.flush()
        for query in ("What are the common side effects of Paracetamol?","What is ibuprofen used for?","How should paracetamol be stored?"):
            if not retrieve(db,query):raise ValueError("Reference retrieval self-check failed: "+query)
        db.commit()
    args.output.write_text(json.dumps({"committed":True,"sources":reports},indent=2),encoding="utf-8")
    print(json.dumps({"committed":True,"documents":len(reports),"chunks":sum(r["chunks"] for r in reports),"report":str(args.output)}))


if __name__=="__main__":main()
