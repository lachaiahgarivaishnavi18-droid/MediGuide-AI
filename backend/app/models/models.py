import uuid
from datetime import datetime, timezone
from sqlalchemy import String, Text, ForeignKey, DateTime, JSON, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from app.database.session import Base


def now():
    return datetime.now(timezone.utc)


class Record:
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, onupdate=now)


class Role(Record, Base):
    __tablename__ = "roles"
    name: Mapped[str] = mapped_column(String(40), unique=True)


class User(Record, Base):
    __tablename__ = "users"
    email: Mapped[str] = mapped_column(String(254), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(100))
    password_hash: Mapped[str] = mapped_column(Text)
    role_id: Mapped[str] = mapped_column(ForeignKey("roles.id"))
    preferences: Mapped[dict] = mapped_column(JSON, default=dict)


class SessionToken(Record, Base):
    __tablename__ = "session_tokens"
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class Conversation(Record, Base):
    __tablename__ = "conversations"
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(160), default="New conversation")


class Message(Record, Base):
    __tablename__ = "messages"
    conversation_id: Mapped[str] = mapped_column(ForeignKey("conversations.id", ondelete="CASCADE"), index=True)
    role: Mapped[str] = mapped_column(String(20))
    content: Mapped[str] = mapped_column(Text)
    response: Mapped[dict | None] = mapped_column(JSON, nullable=True)


class KnowledgeDocument(Record, Base):
    __tablename__ = "knowledge_documents"
    title: Mapped[str] = mapped_column(String(300))
    source_name: Mapped[str] = mapped_column(String(100))
    source_url: Mapped[str] = mapped_column(Text, default="")
    content_hash: Mapped[str] = mapped_column(String(64), unique=True)
    text: Mapped[str] = mapped_column(Text)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)
    approved: Mapped[bool] = mapped_column(default=False)
    synthetic: Mapped[bool] = mapped_column(default=False)
    version: Mapped[int] = mapped_column(default=1)


class KnowledgeChunk(Record, Base):
    __tablename__ = "knowledge_chunks"
    document_id: Mapped[str] = mapped_column(ForeignKey("knowledge_documents.id", ondelete="CASCADE"), index=True)
    text: Mapped[str] = mapped_column(Text)
    section: Mapped[str] = mapped_column(String(300), default="Document")
    ordinal: Mapped[int] = mapped_column(default=0)
    __table_args__ = (UniqueConstraint("document_id", "ordinal"),)


class Medication(Record, Base):
    __tablename__ = "medications"
    generic_name: Mapped[str] = mapped_column(String(200), index=True)
    brand_names: Mapped[list] = mapped_column(JSON, default=list)
    drug_class: Mapped[str] = mapped_column(String(200), default="")
    details: Mapped[dict] = mapped_column(JSON, default=dict)
    document_id: Mapped[str] = mapped_column(ForeignKey("knowledge_documents.id", ondelete="CASCADE"))


class ActiveIngredient(Record, Base):
    __tablename__ = "active_ingredients"
    name: Mapped[str] = mapped_column(String(200), unique=True)


class MedicationIngredient(Record, Base):
    __tablename__ = "medication_ingredients"
    medication_id: Mapped[str] = mapped_column(ForeignKey("medications.id", ondelete="CASCADE"))
    ingredient_id: Mapped[str] = mapped_column(ForeignKey("active_ingredients.id"))
    __table_args__ = (UniqueConstraint("medication_id", "ingredient_id"),)


class MedicationWarning(Record, Base):
    __tablename__ = "medication_warnings"
    medication_id: Mapped[str] = mapped_column(ForeignKey("medications.id", ondelete="CASCADE"))
    chunk_id: Mapped[str] = mapped_column(ForeignKey("knowledge_chunks.id", ondelete="CASCADE"))
    kind: Mapped[str] = mapped_column(String(50))
    text: Mapped[str] = mapped_column(Text)


class MedicationInteraction(Record, Base):
    __tablename__ = "medication_interactions"
    medication_a: Mapped[str] = mapped_column(ForeignKey("medications.id", ondelete="CASCADE"))
    medication_b: Mapped[str] = mapped_column(ForeignKey("medications.id", ondelete="CASCADE"))
    chunk_id: Mapped[str] = mapped_column(ForeignKey("knowledge_chunks.id", ondelete="CASCADE"))
    text: Mapped[str] = mapped_column(Text)


class EducationTopic(Record, Base):
    __tablename__ = "education_topics"
    title: Mapped[str] = mapped_column(String(300))
    category: Mapped[str] = mapped_column(String(80))
    document_id: Mapped[str] = mapped_column(ForeignKey("knowledge_documents.id", ondelete="CASCADE"))


class AgentExecution(Record, Base):
    __tablename__ = "agent_executions"
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    message_id: Mapped[str | None] = mapped_column(ForeignKey("messages.id", ondelete="CASCADE"), nullable=True)
    intent: Mapped[str] = mapped_column(String(80))
    evidence_status: Mapped[str] = mapped_column(String(80))
    safety_status: Mapped[str] = mapped_column(String(80))
    trace: Mapped[list] = mapped_column(JSON, default=list)


class RetrievalLog(Record, Base):
    __tablename__ = "retrieval_logs"
    execution_id: Mapped[str] = mapped_column(ForeignKey("agent_executions.id", ondelete="CASCADE"))
    results: Mapped[list] = mapped_column(JSON, default=list)


class SafetyAlert(Record, Base):
    __tablename__ = "safety_alerts"
    execution_id: Mapped[str] = mapped_column(ForeignKey("agent_executions.id", ondelete="CASCADE"))
    status: Mapped[str] = mapped_column(String(80))
    text: Mapped[str] = mapped_column(Text)


class CitationRecord(Record, Base):
    __tablename__ = "citation_records"
    message_id: Mapped[str] = mapped_column(ForeignKey("messages.id", ondelete="CASCADE"))
    chunk_id: Mapped[str] = mapped_column(ForeignKey("knowledge_chunks.id", ondelete="CASCADE"))


class Feedback(Record, Base):
    __tablename__ = "feedback"
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    message_id: Mapped[str] = mapped_column(ForeignKey("messages.id", ondelete="CASCADE"))
    helpful: Mapped[bool] = mapped_column()


class AuditLog(Record, Base):
    __tablename__ = "audit_logs"
    user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    action: Mapped[str] = mapped_column(String(100))
    resource_id: Mapped[str] = mapped_column(String(100), default="")


class SystemSetting(Record, Base):
    __tablename__ = "system_settings"
    key: Mapped[str] = mapped_column(String(100), unique=True)
    value: Mapped[dict] = mapped_column(JSON, default=dict)
