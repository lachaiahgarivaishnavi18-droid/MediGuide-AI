from app.medication_safety.engine import check_interactions


def run(state):
    if state.get("urgent"):
        return {}
    alerts = list(state.get("alerts", []))
    status = state["safety_status"]
    if state.get("restricted"):
        alerts.append("A pharmacist or prescriber must clarify your personal dose or treatment. MediGuide cannot recommend starting, stopping, replacing, or changing a medicine or dose.")
        status = "NEEDS_PROFESSIONAL_REVIEW"
    if state["intent"] in {"drug_interactions", "missed_dose", "dosage_clarification"}:
        status = "NEEDS_PROFESSIONAL_REVIEW"
        if state["intent"] == "drug_interactions":
            alerts.append(check_interactions(state["db"], state.get("entities", []))["notice"])
        else:
            alerts.append("Medication-specific instructions must be confirmed using your own product leaflet or pharmacist. This chat does not calculate personal dosing.")
    return {"alerts": alerts, "safety_status": status}
