"""Administrator-only, evidence-checked import for structured medication records."""
from sqlalchemy import select
from pydantic import BaseModel, Field
from fastapi import HTTPException
from app.models.models import Medication, KnowledgeDocument, KnowledgeChunk, MedicationWarning, MedicationInteraction, MedicationIngredient, ActiveIngredient, EducationTopic, AuditLog
from app.knowledge_base.provenance import available


class Fact(BaseModel):
    field: str = Field(max_length=80)
    text: str = Field(min_length=1, max_length=10000)
    chunk_id: str


class MedicationImport(BaseModel):
    document_id: str
    generic_name: str = Field(min_length=1, max_length=200)
    brand_names: list[str] = Field(default_factory=list, max_length=30)
    active_ingredients: list[str] = Field(default_factory=list, max_length=30)
    drug_class: str = Field(default="", max_length=200)
    facts: list[Fact] = Field(default_factory=list, max_length=100)


def require_document(db, id):
    doc = db.get(KnowledgeDocument, id)
    if not doc or not available(doc):
        raise HTTPException(422, "An approved, nonsynthetic source document is required")
    return doc


def import_medication(db, payload, user_id):
    doc = require_document(db, payload.document_id)
    # Names and ingredient mappings also need literal support in the approved label.
    for name in [payload.generic_name, *payload.brand_names, *payload.active_ingredients, payload.drug_class]:
        if name and name.casefold() not in doc.text.casefold():
            raise HTTPException(422, "Medication terminology is not present in the approved source")
    details, warnings = {}, []
    for fact in payload.facts:
        chunk = db.get(KnowledgeChunk, fact.chunk_id)
        if not chunk or chunk.document_id != doc.id or fact.text not in chunk.text:
            raise HTTPException(422, "Every fact must be an exact excerpt from a source chunk")
        details.setdefault(fact.field, []).append(fact.text)
        if fact.field in {"warnings", "contraindications", "precautions", "serious_warnings"}:
            warnings.append(fact)
    med = Medication(document_id=doc.id, generic_name=payload.generic_name, brand_names=payload.brand_names, drug_class=payload.drug_class, details=details)
    db.add(med); db.flush()
    for name in payload.active_ingredients:
        ingredient=db.scalar(select(ActiveIngredient).where(ActiveIngredient.name == name.casefold()))
        if not ingredient:
            ingredient=ActiveIngredient(name=name.casefold());db.add(ingredient);db.flush()
        db.add(MedicationIngredient(medication_id=med.id,ingredient_id=ingredient.id))
    for fact in warnings:
        db.add(MedicationWarning(medication_id=med.id,chunk_id=fact.chunk_id,kind=fact.field,text=fact.text))
    db.add(AuditLog(user_id=user_id,action="medication_curated",resource_id=med.id))
    return med


class InteractionImport(BaseModel):
    medication_a: str
    medication_b: str
    chunk_id: str
    text: str = Field(min_length=1,max_length=10000)


def import_interaction(db, payload, user_id):
    a,b = db.get(Medication,payload.medication_a),db.get(Medication,payload.medication_b)
    chunk=db.get(KnowledgeChunk,payload.chunk_id)
    if not a or not b or not chunk or a.id==b.id:
        raise HTTPException(422,"Two different known medications and a source chunk are required")
    require_document(db,a.document_id);require_document(db,b.document_id);require_document(db,chunk.document_id)
    if payload.text not in chunk.text:
        raise HTTPException(422,"Interaction text must be an exact source excerpt")
    # Co-occurrence is only a mechanical gate. Human review must verify the clinical relationship.
    if not all(any(n.casefold() in chunk.text.casefold() for n in [m.generic_name,*m.brand_names]) for m in (a,b)):
        raise HTTPException(422,"Both medication names must occur in the cited passage")
    interaction=MedicationInteraction(**payload.model_dump());db.add(interaction);db.flush()
    db.add(AuditLog(user_id=user_id,action="interaction_curated",resource_id=interaction.id))
    return interaction
