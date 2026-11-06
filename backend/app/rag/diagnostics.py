from collections import Counter
import hashlib
import numpy as np
from sqlalchemy import select
from app.models.models import KnowledgeDocument,KnowledgeChunk
from app.core.config import settings
from app.knowledge_base.provenance import available,active_chunk
from app.rag.retrieval import embed,indexed_corpus,retrieve
from app.rag.query import terminology,medicines_in,topic_of,explicit_subject


def corpus_status(db):
    docs=db.scalars(select(KnowledgeDocument)).all()
    available_ids={d.id for d in docs if available(d)}
    chunks=db.scalars(select(KnowledgeChunk)).all()
    doc_map={d.id:d for d in docs}
    active=[c for c in chunks if c.document_id in available_ids and active_chunk(c,doc_map[c.document_id])]
    count=len(active)
    identity='\n'.join(sorted(f'{d.id}:{d.version}:{d.content_hash}' for d in docs if d.id in available_ids))+ '\n'+'\n'.join(sorted(c.id for c in active))
    return {"documents":len(docs),"approved_documents":sum(d.approved and not d.synthetic for d in docs),
            'corpus_fingerprint':hashlib.sha256(identity.encode()).hexdigest()[:16],
            "available_documents":len(available_ids),"approved_chunks":count,"total_chunks":len(chunks),
            "pending_documents":sum(not d.approved for d in docs),"expired_documents":sum(d.approved and not d.synthetic and not available(d) for d in docs),
            "document_types":dict(Counter(d.metadata_json.get('document_type','unknown') for d in docs)),
            "embedding_provider":settings.embedding_provider,"embedding_model":settings.embedding_model if settings.embedding_provider!='hash' else 'hash-sha256-512-v1',"vector_store":"FAISS","lexical":"BM25Plus",
            "index_mode":"content-keyed persisted FAISS windows and in-process BM25; invalidated by committed corpus changes",
            "index_status":"ready" if count else "empty","cache_entries":indexed_corpus.cache_info().currsize,
            "corpus_warning":"No available approved passages; upload/import and review trusted references." if not count else None}


def diagnose(db,query,k=5,source_name=None):
    vector=embed([query])
    results=retrieve(db,query,k,source_name)
    return {"corpus":corpus_status(db),"query_profile":{"medications":medicines_in(query,terminology(db)),"topic":topic_of(query),"explicit_subject":explicit_subject(query)},
            "query_embedding":{"dimensions":int(vector.shape[1]),"finite":bool(np.isfinite(vector).all()),"norm":float(np.linalg.norm(vector[0]))},
            "result_count":len(results),"results":results,
            "note":"Medication/topic gates precede ranking. BM25/vector/fusion scores are diagnostics, not medical confidence."}
