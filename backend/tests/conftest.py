import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from app.database.session import Base, get_db
from app.main import app
from app.models.models import Role, User
from app.core.security import hash_password
from app.api.routes import attempts


@pytest.fixture(autouse=True)
def deterministic_test_embeddings(monkeypatch):
    # Unit/integration fixtures stay offline. Separate live tests exercise the
    # installed semantic model through the real application process.
    from app.core.config import settings
    from app.rag.retrieval import indexed_corpus
    monkeypatch.setattr(settings,'embedding_provider','hash')
    indexed_corpus.cache_clear()
    yield
    indexed_corpus.cache_clear()


@pytest.fixture
def db():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    from sqlalchemy import event
    @event.listens_for(engine, "connect")
    def foreign_keys(conn, _):
        conn.execute("PRAGMA foreign_keys=ON")
    Base.metadata.create_all(engine)
    with sessionmaker(engine, expire_on_commit=False)() as session:
        session.add_all([Role(id="patient", name="patient"), Role(id="admin", name="admin")])
        session.flush()
        session.add(User(id="admin", email="admin@example.test", name="Test admin", role_id="admin", password_hash=hash_password("test-password-123")))
        session.commit()
        yield session
    engine.dispose()


@pytest.fixture
def client(db):
    attempts.clear()
    app.dependency_overrides[get_db] = lambda: db
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()


@pytest.fixture
def patient(client):
    r = client.post("/api/auth/register", json={"email":"patient@example.test", "name":"Test patient", "password":"test-password-123"})
    assert r.status_code == 201, r.text
    return client


@pytest.fixture
def admin(client):
    r=client.post("/api/auth/login",json={"email":"admin@example.test","password":"test-password-123"})
    assert r.status_code == 200
    return client
