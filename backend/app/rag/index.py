"""Content-versioned local FAISS window index with relational parent provenance."""
import hashlib,json,os,threading,uuid
from functools import lru_cache
import faiss
from rank_bm25 import BM25Plus
from app.core.config import PROJECT_ROOT
from app.rag.embeddings import embed

LOCK=threading.RLock()


def windows(texts):
    pieces=[];owners=[]
    for index,text in enumerate(texts):
        words=text.split()
        for start in range(0,len(words),125):
            pieces.append(' '.join(words[start:start+160]));owners.append(index)
            if start+160>=len(words):break
    return pieces,owners


@lru_cache(maxsize=4)
def indexed_corpus(texts,provider,model):
    from app.rag.retrieval import tokens
    key=hashlib.sha256(json.dumps([3,provider,model,texts],ensure_ascii=False).encode()).hexdigest()
    folder=PROJECT_ROOT/'runtime/indexes';path=folder/(key+'.faiss');manifest=folder/(key+'.json')
    with LOCK:
        index=None;owners=[]
        if provider!='hash' and path.exists() and manifest.exists():
            info=json.loads(manifest.read_text(encoding='utf-8'))
            if info.get('key')==key and info.get('parents')==len(texts):
                index=faiss.read_index(str(path));owners=info['owners']
                if index.ntotal!=len(owners) or any(i<0 or i>=len(texts) for i in owners):raise ValueError('Vector manifest mismatch')
        if index is None:
            pieces,owners=windows(texts)
            matrix=embed(pieces);index=faiss.IndexFlatIP(matrix.shape[1]);index.add(matrix)
            if provider!='hash':
                folder.mkdir(parents=True,exist_ok=True)
                temp=folder/(key+'.'+uuid.uuid4().hex+'.tmp')
                faiss.write_index(index,str(temp));os.replace(temp,path)
                temp.write_text(json.dumps({'key':key,'parents':len(texts),'owners':owners,'dimensions':index.d,'model':model,'provider':provider}),encoding='utf-8');os.replace(temp,manifest)
    return index,BM25Plus([tokens(text) for text in texts]),owners
