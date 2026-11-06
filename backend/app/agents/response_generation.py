from app.agents.safety_escalation import MESSAGE
from app.services.chat_guidance import render_clarification

ABSTENTION = "I could not find sufficient approved evidence in this knowledge base to answer reliably. Please consult the official patient leaflet or a pharmacist or qualified healthcare professional."


def abstention(state):
    from app.rag.query import is_refusal_echo,medicines_in,terminology,topic_of,explicit_subject
    if is_refusal_echo(state.get('query','')):
        return 'That text is a previous no-evidence response, rather than a medical question. Please send the original medicine or health question. A previous response is not medical evidence.'
    query=state.get('retrieval_query',state.get('query',''))
    names=medicines_in(query,terminology(state['db'])) if state.get('db') else []
    topic=topic_of(query)
    if names and topic:
        label={'purpose':'uses','leaflet':'patient leaflet information','missed_dose':'missed-dose instructions'}.get(topic,topic.replace('_',' '))
        reason='I do not have an approved passage covering '+label+' for '+' and '.join(names)+'.'
        if topic=='interactions':reason+=' This does not establish that the combination is safe or unsafe.'
        return reason+' Please check your exact product leaflet or ask a pharmacist or clinician; I will not infer missing medical advice.'
    if explicit_subject(query) and not names:
        return 'I could not find an approved reference for the medicine or health subject named in your question. Check the exact medicine name and product leaflet, or provide the health topic you want explained. I cannot infer medical advice from a similar name.'
    if topic=='leaflet':
        return 'I do not have an approved passage explaining patient leaflets in the available sources. Provide the exact medicine name and leaflet section, or ask a pharmacist to explain the instructions.'
    return ABSTENTION


def render(selected):
    if selected and all('answer_blocks' in item for item in selected):
        parts=['### Source-backed information','These are general patient-education extracts. They do not diagnose symptoms or determine which treatment or dose is suitable for you.']
        for i,item in enumerate(selected):
            title=item['section'].replace('#','').strip()
            parts.append('#### '+title)
            for block in item['answer_blocks']:
                text=block['text']
                parts.append((text if text.startswith('- ') else '- '+text)+f' [{i+1}]')
        if any(item.get('matched_topic')=='leaflet' for item in selected):
            parts.append('For help with a particular leaflet, provide the exact medicine name, strength, and the section or term you want explained.')
        parts.append('### Precautions and next steps\nFollow your own product leaflet and healthcare professional’s instructions. Ask a pharmacist or clinician about medicine suitability, interactions, persistent symptoms, or unclear instructions. For urgent or severe symptoms, seek immediate medical help.')
        attributes=list(dict.fromkeys(item.get('attribution','') for item in selected if item.get('attribution')))
        if attributes:parts.append('### Sources\n'+'\n\n'.join(attributes))
        return '\n\n'.join(parts)
    passages = []
    for i, e in enumerate(selected):
        attribution = e.get("attribution", "")
        passages.append(f"[{i+1}] {e['excerpt']}" + (f"\n\n{attribution}" if attribution else ""))
    return "The approved reference material contains these passages. They are general source information and may not apply to your situation.\n\n" + "\n\n".join(passages)


def run(state):
    if state.get("urgent"):
        answer = MESSAGE
    elif state.get("restricted"):
        answer = "I cannot recommend a personal dose or treatment change. Please ask your prescriber or pharmacist to clarify your existing instructions."
    elif state.get('clarification'):
        answer=render_clarification(state['clarification'])
    elif state["evidence_status"] == "CONFLICTING_EVIDENCE":
        answer = "The source material is marked as conflicting. A pharmacist or clinician should review it before it is used for guidance."
    else:
        answer = render(state["selected"]) if state.get("selected") else abstention(state)
    return {"answer": answer}
