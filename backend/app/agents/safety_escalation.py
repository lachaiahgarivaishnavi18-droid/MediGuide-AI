import re

EMERGENCY_PATTERNS = [r"overdos", r"(?:can't|cannot|unable to|difficulty|trouble|struggling to) breath", r"severe.{0,20}(?:breath|chest pain|allerg)",
                      r"(?:lost|loss of|losing) consciousness", r"unconscious|unresponsive", r"(?:throat|tongue).{0,20}swell", r"anaphylax", r"chest pain", r"suicid|kill myself"]
MESSAGE = "This could require urgent help. Contact your local emergency services or seek immediate medical care now. Do not wait for this chat. MediGuide cannot diagnose an emergency."


def run(state):
    urgent = any(re.search(pattern, state["query"], re.I) for pattern in EMERGENCY_PATTERNS)
    return {"urgent": urgent, "safety_status": "URGENT_ESCALATION" if urgent else "NO_ADDITIONAL_ALERT", "alerts": [MESSAGE] if urgent else []}
