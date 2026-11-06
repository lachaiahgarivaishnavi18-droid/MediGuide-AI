from app.models.models import KnowledgeChunk, KnowledgeDocument
from app.knowledge_base.ingestion import INJECTION
from app.agents.response_generation import render, ABSTENTION,abstention
from app.knowledge_base.provenance import available,active_chunk
from app.services.chat_guidance import clarification_for,render_clarification
from app.services.answer_plan import valid_blocks


def run(state):
    if state.get('selection_invalid'):
        return {'answer':ABSTENTION,'citations':[],'evidence_status':'INSUFFICIENT_EVIDENCE','validation':'rejected'}
    if state.get('clarification'):
        expected=clarification_for(state['db'],state['query'],state.get('context',''))
        if not state.get('urgent') and not state.get('restricted') and expected==state['clarification'] and not state.get('selected') and state['answer']==render_clarification(expected):
            return {'citations':[],'validation':'passed'}
        return {'answer':ABSTENTION,'citations':[],'clarification':None,'evidence_status':'INSUFFICIENT_EVIDENCE','validation':'rejected'}
    valid = []
    for item in state.get("selected", []):
        chunk = state["db"].get(KnowledgeChunk, item["chunk_id"])
        doc = state["db"].get(KnowledgeDocument, item["document_id"])
        if not chunk or not doc or chunk.document_id != doc.id or chunk.text != item["excerpt"] or not available(doc) or not active_chunk(chunk,doc) or INJECTION.search(chunk.text) or not valid_blocks(item,chunk):
            return {"answer": ABSTENTION, "citations": [], "evidence_status": "INSUFFICIENT_EVIDENCE", "validation": "rejected"}
        canonical = {**item, "title":doc.title, "url":doc.source_url, "source_name":doc.source_name, "section":chunk.section,
                     **{key:doc.metadata_json.get(key, "") for key in ("attribution","license_url","retrieved_at","source_updated_at","population_scope")}}
        if any(item.get(key, "") != canonical[key] for key in ("title","url","source_name","section")):
            return {"answer":ABSTENTION,"citations":[],"evidence_status":"INSUFFICIENT_EVIDENCE","validation":"rejected"}
        canonical['supporting_quotes']=[b['text'] for b in item.get('answer_blocks',[])] or [chunk.text]
        valid.append(canonical)
    if valid and state["answer"] != render(valid):
        return {"answer": ABSTENTION, "citations": [], "evidence_status": "INSUFFICIENT_EVIDENCE", "validation": "rejected"}
    if not valid and not state.get("urgent") and not state.get("restricted") and state.get("evidence_status") != "CONFLICTING_EVIDENCE" and state["answer"] != abstention(state):
        return {"answer": ABSTENTION, "citations": [], "evidence_status": "INSUFFICIENT_EVIDENCE", "validation": "rejected"}
    return {"citations": valid, "validation": "passed"}
