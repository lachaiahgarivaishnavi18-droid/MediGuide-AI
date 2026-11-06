import re


INTENTS = [("drug_interactions", r"interact|together|combine"), ("missed_dose", r"missed|forgot|forget|skipped"),
           ("medication_storage", r"stor|refrigerat"), ("side_effects", r"side[ -]?effects?|adverse (?:effects?|reactions?)|unwanted effects?"),
           ("dosage_clarification", r"dose|dosage|mg|schedule|prescri"), ("medication_information", r"medicin|medication|drug" )]


def run(state):
    query = state["query"].lower()
    intent = next((name for name, pattern in INTENTS if re.search(pattern, query)), "general_health_education")
    prevention=bool(re.search(r'(?:reduce|stop).{0,30}(?:risk|catching|spreading|resistance)',query))
    personal_dose=bool(re.search(r'how much.{0,20}(?:i|my)|(?:what|which).{0,15}(?:dose|dosage).{0,25}(?:should i|for me)|(?:can|should) i.{0,20}(?:\d|dose)|my (?:weight|dose)|\bprescribe\b',query))
    changes=bool(re.search(r'\b(?:increase|decrease|double|replace|change|reduce|skip|calculate)\b.{0,45}(?:dose|dosage|mg|tablets?|capsules?|schedule|medicin)|(?:can|should|may|could) i (?:stop|start|switch|replace|double|increase|decrease)|stop taking',query))
    restricted=personal_dose or changes and not prevention
    if re.search(r'diagnos|what (?:illness|disease) do i have|tell me what i have',query):restricted=True
    return {"intent": intent, "restricted": restricted}
