from app.rag.retrieval import retrieve
from app.rag.query import resolve_query,is_refusal_echo
from app.services.chat_guidance import clarification_for


def run(state):
    if state.get("urgent") or state.get("restricted"):
        return {"evidence": []}
    query = resolve_query(state["db"], state["query"], state.get("context", ""))
    evidence=retrieve(state['db'],query)
    clarification=None if evidence or is_refusal_echo(state['query']) else clarification_for(state['db'],state['query'],state.get('context',''))
    return {"evidence":evidence, 'retrieval_query':query,'clarification':clarification}
