from datetime import date


def run(state):
    evidence = state.get("evidence", [])
    # Relevance alone cannot establish correctness. Approval is a human curation gate.
    status = "LIMITED_EVIDENCE" if evidence else "INSUFFICIENT_EVIDENCE"
    if any(e.get("metadata", {}).get("conflicting") for e in evidence):
        status = "CONFLICTING_EVIDENCE"
    return {"evidence_status": status}
