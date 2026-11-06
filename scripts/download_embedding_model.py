"""Explicit one-time model setup; chat-time embedding uses local files only."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'backend'))
from app.rag.embeddings import local_model
from app.core.config import settings

if __name__=='__main__':
    model=local_model(settings.embedding_model,False)
    vector=next(iter(model.embed(['Model installation verification.'])))
    print(f'Cached {settings.embedding_model}: {len(vector)} dimensions. No patient data used.')
