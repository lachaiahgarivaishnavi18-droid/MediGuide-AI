import re
import numpy as np
from sqlalchemy import select
from app.core.config import settings
from app.models.models import KnowledgeChunk,KnowledgeDocument
from app.knowledge_base.provenance import available,active_chunk
from app.rag.query import topic_of,section_topic,terminology,medicines_in,explicit_subject,health_subjects,query_variants,is_refusal_echo
from app.rag.embeddings import embed
from app.rag.index import indexed_corpus

STOP=set('a an the is are what how should can i my it this that of for to and in be about does do me with please tell information some generally usually'.split())


def tokens(text):
    words=re.findall(r'[a-z0-9]+',text.casefold())
    return [w for w in words if w not in STOP]


def retrieve(db,query,k=6,source_name=None):
    if is_refusal_echo(query):return []
    pairs=db.execute(select(KnowledgeChunk,KnowledgeDocument).join(KnowledgeDocument).where(KnowledgeDocument.approved.is_(True),KnowledgeDocument.synthetic.is_(False)).order_by(KnowledgeChunk.id)).all()
    rows=[(c,d) for c,d in pairs if available(d) and active_chunk(c,d) and (not source_name or d.source_name==source_name)]
    if not rows or not tokens(query):return []
    aliases=terminology(db);requested=medicines_in(query,aliases);health=health_subjects(query);subject=explicit_subject(query);topic=topic_of(query)
    neutral={'medicine','medicines','medication','medications','drugs','drug','it','this medicine','my medicine'}
    if subject and re.search(r'\band\b|\bwith\b|\+',subject,re.I):
        for part in re.split(r'\band\b|\bwith\b|\+',subject,flags=re.I):
            if not medicines_in(part,aliases) and not health_subjects(part) and part.strip().casefold() not in neutral|{'alcohol','other medicines'}:return []
    if not requested and subject and not health_subjects(subject) and topic in {'side_effects','storage','dosage','interactions','precautions'} and subject.casefold() not in neutral:
        # Preserve exact identity for an unknown named drug. Semantic similarity
        # must never silently turn it into a different known drug.
        return []
    else:medicine_like=False
    eligible=[];topics={}
    for i,(chunk,doc) in enumerate(rows):
        if topic=='leaflet' and not re.search(r'leaflets?',chunk.text,re.I):continue
        declared=[name.casefold() for name in doc.metadata_json.get('medications',[])]
        concepts=doc.metadata_json.get('health_topics',[])
        passage_topic=section_topic(chunk.section) or section_topic(doc.title)
        if topic=='leaflet' and re.search(r'patient information leaflet|leaflet.*(?:information|instructions)|(?:information|instructions).*leaflet',chunk.text,re.I|re.S):passage_topic='leaflet'
        topics[i]=passage_topic
        if requested:
            if topic=='interactions' and len(requested)>1:
                if not set(requested)&set(declared):continue
                identity_text=(doc.title+' '+chunk.text).casefold()
                if not all(re.search(r'(?<!\w)'+re.escape(name)+r'(?!\w)',identity_text) for name in requested):continue
            elif declared:
                if not set(requested)&set(declared):continue
            elif not all(name in (doc.title+' '+chunk.section).casefold() for name in requested):continue
        elif declared:continue
        elif concepts:
            if medicine_like or not set(health)&set(concepts):continue
        elif subject:
            anchors=set(tokens(subject))
            if not anchors or not anchors.issubset(set(tokens(doc.title+' '+chunk.section))):continue
        if topic=='missed_dose' and passage_topic=='dosage' and re.search(r'forget|miss a dose|missed dose',chunk.text,re.I):passage_topic='missed_dose';topics[i]=passage_topic
        if topic and declared and passage_topic and passage_topic!=topic:continue
        if topic and declared and passage_topic is None:continue
        if not tokens(doc.title+' '+chunk.section+' '+chunk.text):continue
        eligible.append(i)
    if not eligible:return []
    texts=tuple(f'{d.title}\n{c.section}\n{c.text}' for c,d in rows)
    index,bm25,owners=indexed_corpus(texts,settings.embedding_provider,settings.embedding_model)
    variants=query_variants(db,query)
    q=embed(variants)
    if q.shape[1]!=index.d:raise ValueError('Embedding configuration/index dimension mismatch')
    distances,indices=index.search(q,index.ntotal)
    vector=np.full(len(rows),-1.0)
    for scores,ids in zip(distances,indices):
        for score,idx in zip(scores,ids):
            owner=owners[int(idx)];vector[owner]=max(vector[owner],float(score))
    lexical=np.max([bm25.get_scores(tokens(variant)) for variant in variants],axis=0)
    vr={int(v):r for r,v in enumerate(np.argsort(-vector,kind='stable'))}
    lr={int(v):r for r,v in enumerate(np.argsort(-lexical,kind='stable'))}
    fused={i:1/(60+vr[i])+1/(60+lr[i]) for i in eligible}
    def specificity(i):
        section=rows[i][0].section.casefold()
        if topic=='side_effects':
            if re.search(r'serious|severe',query,re.I):return 2 if 'serious' in section else 0
            if 'common' in section:return 2
            if re.search(r'other side effects|reporting',section):return -1
        if topic=='leaflet':return int('leaflet' in section or 'find out more' in section)
        return 0
    ranked=sorted(eligible,key=lambda i:(topics[i]==topic if topic else False,specificity(i), fused[i]+(0.002 if rows[i][1].metadata_json.get('preferred_general_education') else 0)),reverse=True)
    result=[]
    for i in ranked:
        c,d=rows[i];overlap=set(tokens(query))&set(tokens(texts[i]))
        if settings.embedding_provider=='hash':
            if not overlap:continue
        elif vector[i]<settings.semantic_min_score:continue
        # Eligibility establishes the topic/identity context; neural/lexical
        # rankings select relevant passages, never certify medical correctness.
        result.append({'document_id':d.id,'chunk_id':c.id,'source_name':d.source_name,'title':d.title,'url':d.source_url,'section':c.section,'excerpt':c.text,
                       'bm25_score':float(lexical[i]),'vector_score':float(vector[i]),'rrf_score':fused[i],'matched_medications':requested,'matched_health_topics':health,'matched_topic':topic,
                       'metadata':d.metadata_json,**{key:d.metadata_json.get(key,'') for key in ('attribution','license_url','retrieved_at','source_updated_at','population_scope')}})
        if len(result)>=k:break
    return result
