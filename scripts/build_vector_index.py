import sys
import json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"backend"))
import faiss
from sqlalchemy import select
from app.database.session import SessionLocal
from app.models.models import KnowledgeDocument, KnowledgeChunk
from app.rag.index import indexed_corpus
from app.core.config import settings
from app.knowledge_base.provenance import available,active_chunk
from datetime import datetime,timezone
import hashlib

with SessionLocal() as db:
    pairs=db.execute(select(KnowledgeChunk,KnowledgeDocument).join(KnowledgeDocument).where(KnowledgeDocument.approved.is_(True),KnowledgeDocument.synthetic.is_(False)).order_by(KnowledgeChunk.id)).all()
    pairs=[(chunk,doc) for chunk,doc in pairs if available(doc) and active_chunk(chunk,doc)]
    rows=[chunk for chunk,doc in pairs]
    if not rows:
        print("No approved nonsynthetic passages. Index not created.")
    else:
        texts=[f'{doc.title}\n{chunk.section}\n{chunk.text}' for chunk,doc in pairs]
        index,_,owners=indexed_corpus(tuple(texts),settings.embedding_provider,settings.embedding_model)
        destination=Path("runtime/index");destination.mkdir(parents=True,exist_ok=True)
        faiss.write_index(index,str(destination/"knowledge.faiss"))
        (destination/"manifest.json").write_text(json.dumps({"index_version":3,"created_at":datetime.now(timezone.utc).isoformat(),"dimensions":index.d,"provider":settings.embedding_provider,"model":settings.embedding_model if settings.embedding_provider!='hash' else 'hash-sha256-512-v1',"window_parent_indices":owners,"chunk_ids":[r.id for r in rows],"document_versions":{doc.id:doc.version for _,doc in pairs},"content_hash":hashlib.sha256('\n'.join(texts).encode()).hexdigest()},indent=2),encoding="utf-8")
        loaded=faiss.read_index(str(destination/'knowledge.faiss'))
        if loaded.ntotal!=len(owners) or loaded.d!=index.d:raise ValueError('FAISS export roundtrip failed')
        print(f"Exported and reopened {len(rows)} passages ({loaded.d} dimensions). API uses content-keyed approved-corpus caches.")
