from itertools import combinations
from sqlalchemy import select, or_, and_
from app.models.models import Medication, MedicationInteraction, MedicationIngredient, KnowledgeChunk, KnowledgeDocument
from app.knowledge_base.provenance import available


def known_medications(db, names):
    all_meds = db.scalars(select(Medication).join(KnowledgeDocument).where(KnowledgeDocument.approved.is_(True), KnowledgeDocument.synthetic.is_(False))).all()
    all_meds = [m for m in all_meds if available(db.get(KnowledgeDocument,m.document_id))]
    matches, unknown = [], []
    for name in names:
        med = next((m for m in all_meds if name.casefold().strip() in [m.generic_name.casefold(), *[b.casefold() for b in m.brand_names]]), None)
        if med:
            matches.append(med)
        else:
            unknown.append(name)
    return matches, unknown


def check_interactions(db, names):
    meds, unknown = known_medications(db, names)
    findings, duplicates, missing = [], [], []
    for a, b in combinations(meds, 2):
        records = db.scalars(select(MedicationInteraction).where(or_(and_(MedicationInteraction.medication_a == a.id, MedicationInteraction.medication_b == b.id), and_(MedicationInteraction.medication_a == b.id, MedicationInteraction.medication_b == a.id)))).all()
        for record in records:
            chunk = db.get(KnowledgeChunk, record.chunk_id)
            doc = db.get(KnowledgeDocument, chunk.document_id)
            if available(doc) and record.text in chunk.text:
                findings.append({"id": record.id, "medications": [a.generic_name, b.generic_name], "text": record.text, "chunk_id": chunk.id, "document_id": doc.id, "source_url": doc.source_url})
        if not records:
            missing.append([a.generic_name, b.generic_name])
        ingredients_a = set(db.scalars(select(MedicationIngredient.ingredient_id).where(MedicationIngredient.medication_id == a.id)))
        ingredients_b = set(db.scalars(select(MedicationIngredient.ingredient_id).where(MedicationIngredient.medication_id == b.id)))
        if ingredients_a & ingredients_b:
            duplicates.append({"medications": [a.generic_name, b.generic_name], "ingredient_ids": sorted(ingredients_a & ingredients_b)})
    return {"status": "NEEDS_PROFESSIONAL_REVIEW", "findings": findings, "duplicate_ingredients": duplicates, "unknown_medications": unknown, "undocumented_pairs": missing,
            "notice": "This database is incomplete. No documented interaction does not mean a combination is safe. Ask a pharmacist or clinician to review your medicines."}
