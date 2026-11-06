import hashlib
import json
import logging
import secrets
import time
from collections import Counter, defaultdict, deque
from datetime import timedelta
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, Request, Response, UploadFile, File, Form, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import select, func, delete
from app.core.config import settings
from app.core.security import current_user, admin_user, public_user, hash_password, verify_password, digest_token
from app.database.session import get_db
from app.models.models import *
from app.schemas.api import Registration, Login, ChatRequest, ChatResponse, IngestRequest, RetrieveRequest, InteractionRequest, Citation
from app.knowledge_base.ingestion import ingest, extract
from app.rag.retrieval import retrieve
from app.medication_safety.engine import check_interactions
from app.agents.orchestrator import run, NODES
from app.knowledge_base.provenance import available
from app.services.chat_guidance import available_questions
from app.rag.query import medicines_in,terminology,topic_of
from app.core.runtime import RUNTIME

router = APIRouter(prefix="/api")
logger = logging.getLogger("mediguide")
attempts = defaultdict(deque)

from app.services.curation import MedicationImport, InteractionImport, import_medication, import_interaction, require_document


@router.post("/admin/medications", status_code=201)
def curate_medication(payload: MedicationImport, user=Depends(admin_user), db=Depends(get_db)):
    med = import_medication(db, payload, user.id)
    db.commit()
    return {"id": med.id}


@router.post("/admin/interactions", status_code=201)
def curate_interaction(payload: InteractionImport, user=Depends(admin_user), db=Depends(get_db)):
    interaction = import_interaction(db, payload, user.id)
    db.commit()
    return {"id": interaction.id}


@router.post("/admin/education", status_code=201)
def curate_education(payload: dict, user=Depends(admin_user), db=Depends(get_db)):
    doc = require_document(db, str(payload.get("document_id", "")))
    category = payload.get("category", "general")
    if category not in {"general", "medication", "disease"}:
        raise HTTPException(422, "Invalid topic category")
    topic = EducationTopic(title=doc.title, category=category, document_id=doc.id)
    db.add(topic)
    db.commit()
    return {"id": topic.id}


def limit(key, maximum=20, window=60):
    timestamps = attempts[key]
    stamp = time.monotonic()
    while timestamps and timestamps[0] < stamp-window:
        timestamps.popleft()
    if len(timestamps) >= maximum:
        raise HTTPException(429, "Too many requests. Please try again later.")
    timestamps.append(stamp)


def row_dict(row):
    return {column.name: getattr(row, column.name) for column in row.__table__.columns if column.name not in {"password_hash", "token_hash"}}


def owned_conversation(db, user, conversation_id):
    conversation = db.get(Conversation, conversation_id)
    if not conversation or conversation.user_id != user.id:
        raise HTTPException(404, "Conversation not found")
    return conversation


def set_session(db, user, response):
    token = secrets.token_urlsafe(48)
    db.add(SessionToken(user_id=user.id, token_hash=digest_token(token), expires_at=now()+timedelta(hours=settings.session_hours)))
    db.commit()
    response.set_cookie("mediguide_session", token, httponly=True, secure=settings.cookie_secure, samesite="strict", max_age=settings.session_hours*3600, path="/")
    response.headers["Cache-Control"] = "no-store"


@router.post("/auth/register", status_code=201)
def register(payload: Registration, request: Request, response: Response, db=Depends(get_db)):
    limit("register:" + request.client.host, 5, 300)
    if db.scalar(select(User).where(User.email == payload.email)):
        raise HTTPException(409, "Account could not be created with this email")
    role = db.scalar(select(Role).where(Role.name == "patient"))
    if not role:
        raise HTTPException(503, "Database seed is required")
    user = User(email=payload.email, name=payload.name, password_hash=hash_password(payload.password), role_id=role.id)
    db.add(user)
    db.flush()
    db.add(AuditLog(user_id=user.id, action="registered"))
    set_session(db, user, response)
    return public_user(db, user)


@router.post("/auth/login")
def login(payload: Login, request: Request, response: Response, db=Depends(get_db)):
    limit("login:" + request.client.host, 10, 300)
    user = db.scalar(select(User).where(User.email == payload.email.strip().lower()))
    # Hash even on unknown accounts to reduce timing differences.
    stored = user.password_hash if user else hash_password("unavailable-account")
    if not verify_password(payload.password, stored) or not user:
        raise HTTPException(401, "Invalid email or password")
    set_session(db, user, response)
    return public_user(db, user)


@router.post("/auth/logout", status_code=204)
def logout(request: Request, response: Response, user=Depends(current_user), db=Depends(get_db)):
    db.execute(delete(SessionToken).where(SessionToken.token_hash == digest_token(request.cookies.get("mediguide_session", ""))))
    db.commit()
    response.delete_cookie("mediguide_session", path="/")


@router.get("/auth/me")
def me(user=Depends(current_user), db=Depends(get_db)):
    return public_user(db, user)


@router.patch("/auth/me")
def update_me(payload: dict, user=Depends(current_user), db=Depends(get_db)):
    if "name" in payload:
        name = str(payload["name"]).strip()
        if not 1 <= len(name) <= 100:
            raise HTTPException(422, "Name must contain 1–100 characters")
        user.name = name
    user.preferences = {"compact_answers": bool(payload.get("compact_answers", False))}
    db.commit()
    return public_user(db, user)


@router.post("/conversations", status_code=201)
def create_conversation(user=Depends(current_user), db=Depends(get_db)):
    conversation = Conversation(user_id=user.id)
    db.add(conversation)
    db.commit()
    return row_dict(conversation)


@router.get("/conversations")
def conversations(offset: int = Query(0, ge=0), limit_: int = Query(50, alias="limit", ge=1, le=100), user=Depends(current_user), db=Depends(get_db)):
    return [row_dict(c) for c in db.scalars(select(Conversation).where(Conversation.user_id == user.id).order_by(Conversation.updated_at.desc()).offset(offset).limit(limit_))]


@router.delete("/conversations", status_code=204)
def clear_conversations(user=Depends(current_user), db=Depends(get_db)):
    db.execute(delete(Conversation).where(Conversation.user_id == user.id))
    db.add(AuditLog(user_id=user.id, action="conversation_history_deleted"))
    db.commit()


@router.get("/conversations/{conversation_id}")
def conversation_detail(conversation_id: str, user=Depends(current_user), db=Depends(get_db)):
    return row_dict(owned_conversation(db, user, conversation_id))


@router.delete("/conversations/{conversation_id}", status_code=204)
def remove_conversation(conversation_id: str, user=Depends(current_user), db=Depends(get_db)):
    db.delete(owned_conversation(db, user, conversation_id))
    db.commit()


@router.get("/chat/{conversation_id}/messages")
def messages(conversation_id: str, user=Depends(current_user), db=Depends(get_db)):
    owned_conversation(db, user, conversation_id)
    return [row_dict(m) for m in db.scalars(select(Message).where(Message.conversation_id == conversation_id).order_by(Message.created_at))]


@router.get('/chat/suggestions')
def chat_suggestions(user=Depends(current_user),db=Depends(get_db)):
    return available_questions(db)


def chat_work(payload, user, db):
    limit("chat:" + user.id, 20, 60)
    conversation = owned_conversation(db, user, payload.conversation_id) if payload.conversation_id else Conversation(user_id=user.id, title=payload.query[:80])
    db.add(conversation)
    db.flush()
    prior = db.scalars(select(Message).where(Message.conversation_id == conversation.id, Message.role == "user").order_by(Message.created_at.desc()).limit(6)).all()
    db.add(Message(conversation_id=conversation.id, role="user", content=payload.query))
    started = time.perf_counter()
    try:
        result = run(db, payload.query, "\n".join(m.content for m in reversed(prior)))
    except Exception:
        db.rollback()
        logger.exception("Agent execution failed; no response returned")
        db.add(AgentExecution(user_id=user.id, message_id=None, intent="unavailable", evidence_status="SOURCE_UNAVAILABLE", safety_status="VALIDATION_NOT_COMPLETED", trace=[{"agent":"conversation_orchestrator", "status":"failed", "duration_ms":round((time.perf_counter()-started)*1000,2), "error":"Evidence service unavailable; unchecked output discarded"}]))
        db.commit()
        raise HTTPException(503, "The evidence service is unavailable. Please try again or consult a healthcare professional.")
    assistant = Message(conversation_id=conversation.id, role="assistant", content=result["answer"])
    db.add(assistant)
    db.flush()
    from app.rag.diagnostics import corpus_status
    from app.rag.query import query_variants
    normalized=result.get('retrieval_query',payload.query)
    names=medicines_in(normalized,terminology(db))
    followups=available_questions(db,medicine=names[0],exclude_topic=topic_of(normalized),limit=3) if result['citations'] and len(names)==1 else []
    response = ChatResponse(conversation_id=conversation.id, message_id=assistant.id, answer=result["answer"], intent=result["intent"], evidence_status=result["evidence_status"],
                            safety_status=result["safety_status"], citations=[Citation.model_validate(e) for e in result["citations"]], safety_alerts=result["alerts"],
                            follow_up_suggestions=followups,clarification=result.get('clarification'),
                            diagnostics={**RUNTIME,'corpus_fingerprint':corpus_status(db)['corpus_fingerprint'],'original_query':payload.query,'retrieval_query':normalized,'query_variants':query_variants(db,normalized),'retrieved_passages':len(result.get('evidence',[])),'citation_validation':result['validation'],'outcome':'CLARIFICATION_REQUIRED' if result.get('clarification') else result['evidence_status']},
                            limitations=["Educational information only; not diagnosis or treatment.", "Source approval and retrieval do not establish clinical validity."])
    assistant.response = response.model_dump()
    conversation.updated_at = now()
    execution = AgentExecution(user_id=user.id, message_id=assistant.id, intent=result["intent"], evidence_status=result["evidence_status"], safety_status=result["safety_status"], trace=result["trace"])
    db.add(execution)
    db.flush()
    db.add(RetrievalLog(execution_id=execution.id, results=[{k: e[k] for k in ("chunk_id", "bm25_score", "vector_score", "rrf_score")} for e in result.get("evidence", [])]))
    for alert in result["alerts"]:
        db.add(SafetyAlert(execution_id=execution.id, status=result["safety_status"], text=alert))
    for citation in response.citations:
        db.add(CitationRecord(message_id=assistant.id, chunk_id=citation.chunk_id))
    db.commit()
    return response


@router.post("/chat", response_model=ChatResponse)
def chat(payload: ChatRequest, user=Depends(current_user), db=Depends(get_db)):
    return chat_work(payload, user, db)


@router.post("/chat/stream")
def chat_stream(payload: ChatRequest, user=Depends(current_user), db=Depends(get_db)):
    # Buffer until every safety/grounding gate passes; never stream unchecked model tokens.
    result = chat_work(payload, user, db)
    return StreamingResponse(iter(["event: answer\ndata: " + result.model_dump_json() + "\n\n"]), media_type="text/event-stream")


@router.get("/medications")
@router.get("/medications/search")
def medications(q: str = "", offset: int = Query(0, ge=0), limit_: int = Query(50, alias="limit", ge=1, le=100), user=Depends(current_user), db=Depends(get_db)):
    meds = db.scalars(select(Medication).join(KnowledgeDocument).where(KnowledgeDocument.approved.is_(True), KnowledgeDocument.synthetic.is_(False))).all()
    found = []
    for med in meds:
        if not available(db.get(KnowledgeDocument,med.document_id)):
            continue
        ingredients = list(db.scalars(select(ActiveIngredient.name).join(MedicationIngredient, MedicationIngredient.ingredient_id == ActiveIngredient.id).where(MedicationIngredient.medication_id == med.id)))
        if q.casefold() in " ".join([med.generic_name, *med.brand_names, *ingredients]).casefold():
            found.append({**row_dict(med), "active_ingredients": ingredients})
    return found[offset:offset+limit_]


@router.get("/medications/{medication_id}")
@router.get("/medications/{medication_id}/safety")
def medication_detail(medication_id: str, user=Depends(current_user), db=Depends(get_db)):
    record = db.get(Medication, medication_id)
    doc = db.get(KnowledgeDocument, record.document_id) if record else None
    if not record or not doc or not available(doc):
        raise HTTPException(404, "Medication not found")
    med = row_dict(record)
    med["active_ingredients"] = list(db.scalars(select(ActiveIngredient.name).join(MedicationIngredient, MedicationIngredient.ingredient_id == ActiveIngredient.id).where(MedicationIngredient.medication_id == record.id)))
    med["warnings"] = [row_dict(w) for w in db.scalars(select(MedicationWarning).where(MedicationWarning.medication_id == medication_id))]
    med["source"] = row_dict(db.get(KnowledgeDocument, med["document_id"]))
    return med


@router.post("/interactions/check")
def interactions(payload: InteractionRequest, user=Depends(current_user), db=Depends(get_db)):
    return check_interactions(db, payload.medications)


@router.get("/interactions/{interaction_id}")
def interaction_detail(interaction_id: str, user=Depends(current_user), db=Depends(get_db)):
    interaction = db.get(MedicationInteraction, interaction_id)
    if not interaction:
        raise HTTPException(404, "Interaction not found")
    chunk = db.get(KnowledgeChunk, interaction.chunk_id)
    doc = db.get(KnowledgeDocument, chunk.document_id)
    if not available(doc):
        raise HTTPException(404, "Interaction not found")
    return {**row_dict(interaction), "source_url": doc.source_url, "notice": "Requires pharmacist or clinician review"}


@router.get("/education")
@router.get("/education/search")
def education(q: str = "", category: str = "", user=Depends(current_user), db=Depends(get_db)):
    topics = db.scalars(select(EducationTopic).join(KnowledgeDocument).where(KnowledgeDocument.approved.is_(True), KnowledgeDocument.synthetic.is_(False)).limit(100)).all()
    return [row_dict(t) for t in topics if available(db.get(KnowledgeDocument,t.document_id)) and q.lower() in t.title.lower() and (not category or t.category == category)]


@router.get("/education/{topic_id}")
def education_detail(topic_id: str, user=Depends(current_user), db=Depends(get_db)):
    topic = db.get(EducationTopic, topic_id)
    doc = db.get(KnowledgeDocument, topic.document_id) if topic else None
    if not doc or not available(doc):
        raise HTTPException(404, "Topic not found")
    return {**row_dict(topic), "document": row_dict(doc)}


@router.get("/knowledge/documents")
def documents(offset: int = Query(0, ge=0), limit_: int = Query(50, alias="limit", ge=1, le=100), user=Depends(admin_user), db=Depends(get_db)):
    return [{k: v for k, v in row_dict(d).items() if k != "text"} for d in db.scalars(select(KnowledgeDocument).order_by(KnowledgeDocument.created_at.desc()).offset(offset).limit(limit_))]


@router.get("/knowledge/documents/{document_id}")
def document_detail(document_id: str, user=Depends(admin_user), db=Depends(get_db)):
    doc = db.get(KnowledgeDocument, document_id)
    if not doc:
        raise HTTPException(404, "Document not found")
    return {**row_dict(doc), "chunks": [row_dict(c) for c in db.scalars(select(KnowledgeChunk).where(KnowledgeChunk.document_id == doc.id).order_by(KnowledgeChunk.ordinal))]}


@router.post("/knowledge/documents/ingest", status_code=201)
def ingest_text(payload: IngestRequest, user=Depends(admin_user), db=Depends(get_db)):
    doc, created = ingest(db, payload, user.id)
    db.commit()
    return {"id": doc.id, "created": created, "approved": doc.approved}


@router.post("/knowledge/documents/upload", status_code=201)
async def upload(file: UploadFile = File(...), title: str = Form(...), source_name: str = Form(...), source_url: str = Form(""), medications: str = Form(""), user=Depends(admin_user), db=Depends(get_db)):
    data = await file.read(settings.max_upload_bytes+1)
    if len(data) > settings.max_upload_bytes:
        raise HTTPException(413, "Document exceeds 10 MB limit")
    try:
        text = extract(data, Path(file.filename or "").suffix.lower())
        names=list(dict.fromkeys(name.strip().casefold() for name in medications.split(',') if name.strip()))
        if len(names)>10 or any(len(name)>200 or name not in text.casefold() for name in names):
            raise HTTPException(422,"Medicine tags must occur in the document text (maximum 10 names)")
        payload = IngestRequest(title=title, source_name=source_name, source_url=source_url, text=text, metadata={"document_type": Path(file.filename or "").suffix.lower(),"medications":names})
        doc, created = ingest(db, payload, user.id)
        db.commit()
        return {"id": doc.id, "created": created, "approved": False}
    except HTTPException:
        raise
    except ValueError as exc:
        raise HTTPException(422, "PDF has no extractable text. OCR is required before indexing." if "OCR" in str(exc) else "Document content or metadata is invalid; check file type and source fields.")
    except Exception:
        raise HTTPException(422, "Document could not be extracted. Check file type, encoding, and content.")


@router.post("/knowledge/dailymed/{set_id}", status_code=201)
def import_dailymed(set_id: str, user=Depends(admin_user), db=Depends(get_db)):
    from app.knowledge_base.connectors import fetch_dailymed
    try:
        doc, created = ingest(db, IngestRequest(**fetch_dailymed(set_id)), user.id)
        db.commit()
        return {"id": doc.id, "created": created, "approved": False}
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(422, "DailyMed source unavailable or label invalid; no substitute data was imported")


@router.patch("/knowledge/documents/{document_id}")
def approve_document(document_id: str, payload: dict, user=Depends(admin_user), db=Depends(get_db)):
    doc = db.get(KnowledgeDocument, document_id)
    if not doc:
        raise HTTPException(404, "Document not found")
    if doc.synthetic and payload.get("approved"):
        raise HTTPException(422, "Synthetic documents cannot be approved for patient retrieval")
    doc.approved = payload.get("approved") is True
    doc.version += 1
    db.add(AuditLog(user_id=user.id, action="document_approval_changed", resource_id=doc.id))
    db.commit()
    return {"id": doc.id, "approved": doc.approved, "version": doc.version}


@router.delete("/knowledge/documents/{document_id}", status_code=204)
def delete_document(document_id: str, user=Depends(admin_user), db=Depends(get_db)):
    doc = db.get(KnowledgeDocument, document_id)
    if not doc:
        raise HTTPException(404, "Document not found")
    db.add(AuditLog(user_id=user.id, action="document_deleted", resource_id=doc.id))
    db.delete(doc)
    db.commit()


@router.post("/knowledge/retrieve")
def test_retrieve(payload: RetrieveRequest, user=Depends(admin_user), db=Depends(get_db)):
    return retrieve(db, payload.query, payload.k, payload.source_name)


@router.get("/knowledge/status")
def knowledge_status(user=Depends(current_user), db=Depends(get_db)):
    from app.rag.diagnostics import corpus_status
    return {**corpus_status(db),"connectors":[{"name":"DailyMed SPL","implemented":True}, {"name":"Fixed NHS/HPRA reference manifest","implemented":True}, {"name":"Administrator document upload","implemented":True}]}


@router.post("/knowledge/diagnose")
def diagnose_retrieval(payload: RetrieveRequest, user=Depends(admin_user), db=Depends(get_db)):
    from app.rag.diagnostics import diagnose
    return diagnose(db,payload.query,payload.k,payload.source_name)


@router.post("/agents/run", response_model=ChatResponse)
def agent_run(payload: ChatRequest, user=Depends(current_user), db=Depends(get_db)):
    return chat_work(payload, user, db)


@router.get("/agents/status")
def agent_status(user=Depends(current_user)):
    return {"agents": [name for name, _ in NODES]+["conversation_orchestrator"], "orchestration": "LangGraph", "reasoning_visibility": "operational metadata only"}


@router.get("/agents/executions")
def executions(user=Depends(current_user), db=Depends(get_db)):
    return [row_dict(e) for e in db.scalars(select(AgentExecution).where(AgentExecution.user_id == user.id).order_by(AgentExecution.created_at.desc()).limit(100))]


@router.get("/agents/executions/{execution_id}")
def execution_detail(execution_id: str, user=Depends(current_user), db=Depends(get_db)):
    execution = db.get(AgentExecution, execution_id)
    if not execution or execution.user_id != user.id:
        raise HTTPException(404, "Execution not found")
    return {**row_dict(execution), "retrieval": [row_dict(r) for r in db.scalars(select(RetrievalLog).where(RetrievalLog.execution_id == execution.id))]}


@router.get("/analytics/overview")
@router.get("/analytics/queries")
@router.get("/analytics/retrieval")
@router.get("/analytics/safety")
def analytics(user=Depends(current_user), db=Depends(get_db)):
    runs = db.scalars(select(AgentExecution).where(AgentExecution.user_id == user.id)).all()
    count = len(runs)
    return {"scope": "Your account activity", "synthetic": False, "conversations": db.scalar(select(func.count()).select_from(Conversation).where(Conversation.user_id == user.id)),
            "queries": count, "query_categories": dict(Counter(e.intent for e in runs)), "evidence_statuses": dict(Counter(e.evidence_status for e in runs)),
            "retrieval_success_rate": sum(e.evidence_status == "LIMITED_EVIDENCE" for e in runs)/count if count else None,
            "citation_validation_rate": sum(any(t["agent"] == "citation_validation" and t.get("validation") == "passed" for t in e.trace) for e in runs)/count if count else None,
            "insufficient_evidence_rate": sum(e.evidence_status == "INSUFFICIENT_EVIDENCE" for e in runs)/count if count else None,
            "safety_escalations": sum(e.safety_status == "URGENT_ESCALATION" for e in runs), "source_status": knowledge_status(user, db)}


@router.get("/system/status")
def system_status():
    return {"status": "ok", "provider": settings.llm_provider, "mode": "educational; not clinically validated", "version": "0.1.0",**RUNTIME}
