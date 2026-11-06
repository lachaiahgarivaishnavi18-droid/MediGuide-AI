"""Source-derived questions and explicit name clarification, never silent drug correction."""
import re
from difflib import SequenceMatcher
from sqlalchemy import select
from app.models.models import KnowledgeDocument,KnowledgeChunk
from app.knowledge_base.provenance import available,active_chunk
from app.rag.query import terminology,medicines_in,resolve_query,topic_of,section_topic,explicit_subject

TEMPLATES={"side_effects":"What are the side effects of {medicine}?", "purpose":"What is {medicine} used for?", "storage":"How should {medicine} be stored?", "precautions":"What precautions are listed for {medicine}?"}


def covered_topics(db):
    result={}
    rows=db.execute(select(KnowledgeChunk,KnowledgeDocument).join(KnowledgeDocument).order_by(KnowledgeDocument.created_at,KnowledgeChunk.ordinal)).all()
    for chunk,doc in rows:
        if not available(doc) or not active_chunk(chunk,doc):continue
        topic=section_topic(chunk.section)
        if topic not in TEMPLATES:continue
        for name in doc.metadata_json.get('medications',[]):
            result.setdefault(name.casefold(),set()).add(topic)
    return result


def available_questions(db,medicine=None,exclude_topic=None,limit=6):
    coverage=covered_topics(db)
    questions=[template.format(medicine=name) for topic,template in TEMPLATES.items() for name,topics in coverage.items()
            if topic in topics and topic!=exclude_topic and (not medicine or name==medicine)][:limit]
    if not medicine:
        from app.rag.query import HEALTH_ALIASES
        concepts={topic for doc in db.scalars(select(KnowledgeDocument)) if available(doc) for topic in doc.metadata_json.get('health_topics',[])}
        questions+=['What are the symptoms of '+name+'?' for name in ('dehydration','common cold') if name in concepts]
        questions+=['What are antibiotics used for?'] if 'antibiotics' in concepts else []
    return questions[:limit+3]


def edit_distance(a,b):
    previous=list(range(len(b)+1))
    for i,left in enumerate(a,1):
        current=[i]
        for j,right in enumerate(b,1):current.append(min(current[-1]+1,previous[j]+1,previous[j-1]+(left!=right)))
        previous=current
    return previous[-1]


def clarification_for(db,query,context=''):
    aliases=terminology(db)
    resolved=resolve_query(db,query,context)
    if medicines_in(resolved,aliases):return None
    words=list(dict.fromkeys(re.findall(r"[A-Za-z][A-Za-z-]{4,}",query)))
    options=[]
    for word in words:
        for alias,canonical in aliases.items():
            if ' ' in alias:continue
            if len(word)>40 or len(alias)>40 or abs(len(word)-len(alias))>2:continue
            distance=edit_distance(word.casefold(),alias)
            ratio=SequenceMatcher(None,word.casefold(),alias).ratio()
            if 0<distance<=(2 if len(alias)>=7 else 1) and ratio>=0.8:
                suggested=re.sub(r'(?<!\w)'+re.escape(word)+r'(?!\w)',canonical,query,flags=re.I).strip()
                options.append((distance,-ratio,word,canonical,suggested))
    if options:
        options.sort()
        candidates=[];seen=set()
        for _,_,word,name,suggested in options:
            if name not in seen:
                seen.add(name);candidates.append({'medicine':name,'suggested_query':suggested})
            if len(candidates)==3:break
        return {'kind':'medicine_spelling','input_name':options[0][2],'candidates':candidates}
    subject=explicit_subject(query)
    neutral={'a','the','my','medicine','medicines','medication','medications','storage','leaflet','information'}
    if subject and subject.casefold() not in neutral:return None
    if not re.search(r'medicin|medication|pharma|leaflet|side[ -]?effect|storage',query,re.I):return None
    topic=topic_of(query)
    coverage=covered_topics(db)
    candidates=[{'medicine':name,'suggested_query':TEMPLATES[topic if topic in TEMPLATES else 'purpose'].format(medicine=name)}
                for name,topics in coverage.items() if (topic in topics if topic else 'purpose' in topics)]
    if candidates:return {'kind':'medicine_required','input_name':'','candidates':candidates[:4]}
    return None


def render_clarification(clarification):
    if clarification['kind']=='medicine_spelling':
        return f"I could not match ‘{clarification['input_name']}’ to an exact verified medicine name. Please check the name on the packet and confirm a name below. Similar names can refer to different medicines; I have not assumed they are equivalent."
    return 'The available references are medicine-specific. Choose a source-backed question below, or enter the exact medicine name and what you would like to understand.'
