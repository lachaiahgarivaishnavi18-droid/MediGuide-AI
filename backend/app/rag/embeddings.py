import hashlib
import re
from functools import lru_cache
import faiss
import numpy as np
from app.core.config import settings,PROJECT_ROOT


@lru_cache(maxsize=2)
def local_model(model_name,local_only=True):
    from fastembed import TextEmbedding
    return TextEmbedding(model_name=model_name,cache_dir=str(PROJECT_ROOT/'runtime/models'),threads=2,local_files_only=local_only)


def embed(texts):
    if settings.embedding_provider=='fastembed':
        result=np.asarray(list(local_model(settings.embedding_model,settings.embedding_local_files_only).embed(texts,batch_size=32)),dtype='float32')
    elif settings.embedding_provider=='sentence-transformers':
        from sentence_transformers import SentenceTransformer
        result=np.asarray(sentence_model(settings.embedding_model).encode(texts,normalize_embeddings=True),dtype='float32')
    elif settings.embedding_provider=='hash':
        result=np.zeros((len(texts),512),dtype='float32')
        for row,text in enumerate(texts):
            for word in re.findall(r'[a-z0-9]+',text.casefold()):
                digest=hashlib.sha256(word.encode()).digest()
                result[row,int.from_bytes(digest[:4],'little')%512]+=1 if digest[4]%2 else -1
    else:raise ValueError('Unsupported embedding provider')
    if result.ndim!=2 or not np.isfinite(result).all():raise ValueError('Invalid embedding matrix')
    faiss.normalize_L2(result)
    return result


@lru_cache(maxsize=1)
def sentence_model(name):
    from sentence_transformers import SentenceTransformer
    return SentenceTransformer(name)
