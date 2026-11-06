from app.services.llm import select_passages
from app.services.answer_plan import with_answer_plans


def run(state):
    if state.get("urgent") or state.get("restricted") or state["evidence_status"] in {"CONFLICTING_EVIDENCE", "INSUFFICIENT_EVIDENCE"}:
        return {"selected": []}
    query=state.get('retrieval_query',state['query'])
    proposed=select_passages(query,state['evidence'])
    # A provider may select retrieved passages, never substitute or modify one.
    if any(item not in state['evidence'] for item in proposed):return {'selected':[],'selection_invalid':True}
    selected=with_answer_plans(query,proposed)
    return {"selected":selected,**({'evidence_status':'INSUFFICIENT_EVIDENCE'} if not selected else {})}
