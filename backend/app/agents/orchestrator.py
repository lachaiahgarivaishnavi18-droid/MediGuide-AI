import time
from langgraph.graph import StateGraph, START, END
from app.agents.state import AgentState
from app.agents import query_understanding, safety_escalation, entity_recognition, knowledge_retrieval, medication_safety, evidence_evaluation, patient_education, response_generation, citation_validation

NODES = [("query_understanding", query_understanding.run), ("safety_escalation", safety_escalation.run),
         ("entity_recognition", entity_recognition.run), ("knowledge_retrieval", knowledge_retrieval.run),
         ("medication_safety", medication_safety.run), ("evidence_evaluation", evidence_evaluation.run),
         ("patient_education", patient_education.run), ("response_generation", response_generation.run),
         ("citation_validation", citation_validation.run)]


def instrument(name, fn):
    def execute(state):
        start = time.perf_counter()
        result = fn(state)
        return {**result, "trace": [*state.get("trace", []), {"agent": name, "status": "completed", "validation": result.get("validation"), "duration_ms": round((time.perf_counter()-start)*1000, 2)}]}
    return execute


builder = StateGraph(AgentState)
for name, fn in NODES:
    builder.add_node(name, instrument(name, fn))
builder.add_edge(START, "query_understanding")
builder.add_edge("query_understanding", "safety_escalation")
builder.add_conditional_edges("safety_escalation", lambda s: "urgent" if s["urgent"] else "normal", {"urgent": "evidence_evaluation", "normal": "entity_recognition"})
for left, right in [("entity_recognition", "knowledge_retrieval"), ("knowledge_retrieval", "medication_safety"), ("medication_safety", "evidence_evaluation"), ("evidence_evaluation", "patient_education"), ("patient_education", "response_generation"), ("response_generation", "citation_validation")]:
    builder.add_edge(left, right)
builder.add_edge("citation_validation", END)
graph = builder.compile()


def run(db, query, context=""):
    start = time.perf_counter()
    result = graph.invoke({"db": db, "query": query, "context": context, "trace": [], "selected": [], "evidence": [], "entities": [], "alerts": [],'clarification':None}, {"recursion_limit": 20})
    result["trace"].append({"agent": "conversation_orchestrator", "status": "completed", "duration_ms": round((time.perf_counter()-start)*1000, 2)})
    return result
