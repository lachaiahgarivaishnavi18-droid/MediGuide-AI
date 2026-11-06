import re
from sqlalchemy import select
from app.models.models import Medication


def run(state):
    query = state["query"]
    from app.rag.query import medicines_in,terminology
    entities = medicines_in(query,terminology(state['db']))
    for med in state["db"].scalars(select(Medication)):
        for name in [med.generic_name, *med.brand_names]:
            if re.search(r"(?<!\w)" + re.escape(name) + r"(?!\w)", query, re.I):
                entities.append(med.generic_name)
    entities.extend(re.findall(r"\b\d+(?:\.\d+)?\s*(?:mg|mcg|ml|g)\b", query, re.I))
    return {"entities": list(dict.fromkeys(entities))}
