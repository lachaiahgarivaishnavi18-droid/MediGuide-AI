from typing import Literal
from pydantic import BaseModel, Field, field_validator


class Registration(BaseModel):
    email: str = Field(min_length=5, max_length=254)
    password: str = Field(min_length=12, max_length=128)
    name: str = Field(min_length=1, max_length=100)

    @field_validator("email")
    @classmethod
    def email_valid(cls, value):
        value = value.strip().lower()
        if "@" not in value or "." not in value.rsplit("@", 1)[-1]:
            raise ValueError("A valid email address is required")
        return value


class Login(BaseModel):
    email: str = Field(max_length=254)
    password: str = Field(max_length=128)


class ChatRequest(BaseModel):
    query: str = Field(min_length=2, max_length=4000)
    conversation_id: str | None = None

    @field_validator('query',mode='before')
    @classmethod
    def trim_query(cls,value):
        return value.strip() if isinstance(value,str) else value


class Citation(BaseModel):
    document_id: str
    chunk_id: str
    source_name: str
    title: str
    url: str
    section: str
    excerpt: str
    attribution: str = ""
    license_url: str = ""
    retrieved_at: str = ""
    source_updated_at: str = ""
    population_scope: str = ""
    supporting_quotes: list[str] = []


class ClarificationCandidate(BaseModel):
    medicine: str
    suggested_query: str


class Clarification(BaseModel):
    kind: Literal['medicine_spelling','medicine_required']
    input_name: str
    candidates: list[ClarificationCandidate]


class ChatResponse(BaseModel):
    conversation_id: str
    message_id: str
    answer: str
    intent: str
    evidence_status: Literal["HIGH_CONFIDENCE_EVIDENCE", "LIMITED_EVIDENCE", "CONFLICTING_EVIDENCE", "INSUFFICIENT_EVIDENCE", "SOURCE_UNAVAILABLE"]
    safety_status: str
    citations: list[Citation] = []
    safety_alerts: list[str] = []
    follow_up_suggestions: list[str] = []
    limitations: list[str] = []
    clarification: Clarification | None = None
    diagnostics: dict = {}


class IngestRequest(BaseModel):
    title: str = Field(min_length=1, max_length=300)
    source_name: str = Field(min_length=1, max_length=100)
    source_url: str = Field(default="", max_length=2000)
    text: str = Field(min_length=20, max_length=500000)
    approved: bool = False
    synthetic: bool = False
    metadata: dict = {}


class RetrieveRequest(BaseModel):
    query: str = Field(min_length=2, max_length=4000)
    k: int = Field(default=5, ge=1, le=20)
    source_name: str | None = None


class InteractionRequest(BaseModel):
    medications: list[str] = Field(min_length=2, max_length=10)
