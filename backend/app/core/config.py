from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator
from pathlib import Path
from sqlalchemy.engine import make_url

PROJECT_ROOT=Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=PROJECT_ROOT/".env", extra="ignore")
    database_url: str = "sqlite:///./mediguide.db"
    environment: str = "development"
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    cookie_secure: bool = False
    llm_provider: str = "extractive"
    llm_base_url: str = "https://api.openai.com/v1"
    llm_api_key: str = ""
    llm_model: str = ""
    embedding_provider: str = "fastembed"
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    semantic_min_score: float = 0.30
    embedding_local_files_only: bool = True
    admin_email: str = ""
    admin_password: str = ""
    max_upload_bytes: int = 10 * 1024 * 1024
    session_hours: int = 12

    @field_validator('database_url')
    @classmethod
    def anchor_sqlite(cls,value):
        if value.startswith('postgres://'):
            value='postgresql+psycopg://'+value[len('postgres://'):]
        elif value.startswith('postgresql://'):
            value='postgresql+psycopg://'+value[len('postgresql://'):]
        url=make_url(value)
        if url.get_backend_name()=='sqlite' and url.database and url.database!=':memory:' and not Path(url.database).is_absolute():
            return url.set(database=str((PROJECT_ROOT/url.database).resolve())).render_as_string(hide_password=False)
        return value


settings = Settings()
