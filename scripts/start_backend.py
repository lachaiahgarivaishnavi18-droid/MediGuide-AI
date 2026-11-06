"""Container startup: validate durable storage, migrate, seed and load sources."""
import os,sys,subprocess
from pathlib import Path
from urllib.parse import urlsplit
from sqlalchemy.engine import make_url

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'backend'))


def validate_production(config):
    if config.environment!='production':return
    if make_url(config.database_url).get_backend_name()!='postgresql':
        raise ValueError('Production container requires a persistent PostgreSQL DATABASE_URL; local SQLite is not used.')
    if not config.cookie_secure:raise ValueError('Production requires COOKIE_SECURE=true.')
    origins=[origin for origin in config.cors_origins.split(',') if origin]
    for origin in origins:
        url=urlsplit(origin)
        if url.scheme!='https' or not url.hostname or url.username or url.password or url.path or url.query or url.fragment or url.hostname in {'localhost','127.0.0.1'}:
            raise ValueError('CORS_ORIGINS must contain exact HTTPS frontend origins without trailing slashes.')


def needs_reference_import(db):
    from sqlalchemy import select
    from app.models.models import KnowledgeDocument
    from app.knowledge_base.provenance import available
    from import_trusted_references import deployment_references
    expected={item['id'] for item in deployment_references()}
    present={doc.metadata_json.get('reference_id') for doc in db.scalars(select(KnowledgeDocument)) if available(doc)}
    return not expected.issubset(present)


def main():
    from app.core.config import settings
    validate_production(settings)
    environment={**os.environ,'PYTHONPATH':str(ROOT/'backend')}
    def run(*args):subprocess.run([sys.executable,*args],cwd=ROOT,env=environment,check=True)
    run('-m','alembic','-c','backend/alembic.ini','upgrade','head')
    run('scripts/seed_database.py')
    if os.environ.get('IMPORT_TRUSTED_REFERENCES_ON_START','false').lower()=='true':
        from app.database.session import SessionLocal
        with SessionLocal() as db:refresh=needs_reference_import(db)
        if refresh:run('scripts/import_trusted_references.py')
    port=os.environ.get('PORT','8000')
    if not port.isdecimal() or not 1<=int(port)<=65535:raise ValueError('PORT must be a valid TCP port.')
    os.chdir(ROOT)
    os.environ.update(environment)
    os.execv(sys.executable,[sys.executable,'-m','uvicorn','app.main:app','--host','0.0.0.0','--port',port])

if __name__=='__main__':main()
