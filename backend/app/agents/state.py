from typing import TypedDict, Any


class AgentState(TypedDict, total=False):
    query: str
    context: str
    db: Any
    intent: str
    entities: list[str]
    urgent: bool
    restricted: bool
    evidence: list[dict]
    evidence_status: str
    safety_status: str
    alerts: list[str]
    answer: str
    selected: list[dict]
    selection_invalid: bool
    citations: list[dict]
    trace: list[dict]
    validation: str
    retrieval_query: str
    clarification: dict | None
