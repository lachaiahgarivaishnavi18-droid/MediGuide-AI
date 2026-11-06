import sys
from pathlib import Path
from types import SimpleNamespace
import pytest
from app.core.config import Settings

sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'scripts'))
from start_backend import validate_production


@pytest.mark.parametrize('scheme',['postgres','postgresql','postgresql+psycopg'])
def test_render_connection_string_selects_installed_driver(scheme):
    config=Settings(_env_file=None,database_url=f'{scheme}://user:password@db.example.com/mediguide')
    assert config.database_url=='postgresql+psycopg://user:password@db.example.com/mediguide'


def test_production_prevents_ephemeral_database_and_unsafe_origin():
    config=SimpleNamespace(environment='production',database_url='sqlite:///local.db',cookie_secure=True,cors_origins='https://mediguide.example.com')
    with pytest.raises(ValueError,match='persistent PostgreSQL'):validate_production(config)
    config.database_url='postgresql+psycopg://user:password@db.example.com/mediguide'
    validate_production(config)
    for origin in ['http://localhost:5173','*','https://mediguide.example.com/','https://mediguide.example.com/path']:
        config.cors_origins=origin
        with pytest.raises(ValueError,match='exact HTTPS'):validate_production(config)


def test_production_import_excludes_local_only_who_material(monkeypatch):
    from import_trusted_references import deployment_references
    from app.core.config import settings
    monkeypatch.setattr(settings,'environment','production')
    assert deployment_references() and all(r['source']!='WHO' for r in deployment_references())
