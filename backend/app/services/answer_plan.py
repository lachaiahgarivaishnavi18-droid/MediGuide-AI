"""Readable extractive answer plans. Every medical block is an exact source span."""
import re,math
from app.rag.query import topic_of,section_topic


def plan_passage(query,item):
    text=item['excerpt'];topic=topic_of(query)
    paragraphs=[]
    for match in re.finditer(r'\S(?:.*?\S)?(?=\n\s*\n|\Z)',text,re.S):
        value=match.group().strip()
        if value.startswith('#') or re.fullmatch(r'(?:Page\s+)?\d+',value) or len(value)<18:continue
        if len(value)<100 and not value.startswith('- ') and not re.search(r'[.!?:;\n]',value):continue
        if re.search(r'^(?:try a different|stop taking|start taking|switch to)',value,re.I):continue
        if topic!='dosage' and re.search(r'\b(?:take|give)\b.{0,40}\b\d+\s*(?:mg|tablets?|capsules?)',value,re.I):continue
        # Lists retain their immediately preceding context (including Do/Don't,
        # frequency, severity or population qualifiers), never isolated symptoms.
        start=match.start();end=match.end()
        if value.startswith('- ') or re.match(r'(?:This|These|They|It)\b',value) and topic=='leaflet':
            previous=text[:start].rstrip();boundary=previous.rfind('\n\n')+2
            context=previous[boundary:]
            if context and not context.startswith('#') and len(context)<350:start=boundary
        paragraphs.append((start,end,text[start:end]))
    if not paragraphs:return []
    # Keep introductory clauses with the immediately following list; otherwise
    # an extracted colon could conceal the actual restrictions or examples.
    for i,(start,end,value) in enumerate(paragraphs):
        if value.rstrip().endswith(':') and i+1<len(paragraphs):
            next_start,next_end,next_value=paragraphs[i+1]
            if next_end>end and (next_start<=end or (text[end:next_start].strip()=='' and next_value.lstrip().startswith('- '))):
                paragraphs[i]=(start,next_end,text[start:next_end])
    from app.rag.retrieval import tokens
    query_terms=set(tokens(query))
    terms=[set(tokens(p[2])) for p in paragraphs]
    weights={word:1+math.log((len(terms)+1)/(1+sum(word in words for words in terms))) for word in query_terms}
    # Rare query anchors (e.g. the second medicine in an interaction) outweigh
    # repeated section words. Do not penalize a safety list for its length.
    scores=[sum(weights[word] for word in query_terms&words) for words in terms]
    # Preserve the section's opening frequency/context statement, then one
    # relevant supporting block. Never shorten a selected medical sentence.
    best=max(range(len(paragraphs)),key=lambda i:scores[i])
    chosen={0,best}
    if topic=='leaflet' and not re.search(r'leaflet',paragraphs[0][2],re.I):chosen={best}
    if topic=='side_effects' and re.search(r'serious|severe',query,re.I):
        urgent=next((i for i,p in enumerate(paragraphs) if re.search(r'call|immediate|urgent',p[2],re.I) and '\n- ' in p[2]),None)
        if urgent is not None:chosen.add(urgent)
    ranges=[]
    for i in sorted(chosen):
        start,end,value=paragraphs[i]
        ranges.append((start,end))
    merged=[]
    for start,end in sorted(ranges):
        if merged and start<=merged[-1][1]:merged[-1]=(merged[-1][0],max(end,merged[-1][1]))
        else:merged.append((start,end))
    return [{'start':start,'end':end,'text':text[start:end]} for start,end in merged]


def with_answer_plans(query,evidence):
    from app.rag.retrieval import tokens
    topic=topic_of(query)
    matching=[item for item in evidence if section_topic(item['section'])==topic] if topic else []
    candidates=matching or evidence
    generic=set('side effects common medicine medicines medication medications drug drugs used purpose storage information available dosage precautions symptoms causes prevention make feel feeling take taking should could would'.split())
    medicine_words={word for item in evidence for name in item.get('matched_medications',[]) for word in tokens(name)}
    anchors=set(tokens(query))-generic-medicine_words
    result=[];covered=set();medicines=set();seen=[]
    for item in candidates:
        blocks=plan_passage(query,item)
        blocks=[b for b in blocks if not any(' '.join(b['text'].split()) in prior for prior in seen)]
        if not blocks:continue
        words=set(tokens(' '.join(b['text'] for b in blocks)))
        primary=set(item.get('metadata',{}).get('medications',[]))
        # Keep a further source only when it adds a requested detail, another
        # requested medicine, or an explicit safety instruction. Repeated
        # introductory sections do not make the answer more informative.
        safety=any(re.search(r'\b(?:do not|must not|call|urgent|immediate)\b',b['text'],re.I) for b in blocks)
        if result and not ((anchors&words)-covered or primary-medicines or safety):continue
        result.append({**item,'answer_blocks':blocks})
        covered.update(words);medicines.update(primary);seen.extend(' '.join(b['text'].split()) for b in blocks)
    return result


def valid_blocks(item,chunk):
    blocks=item.get('answer_blocks')
    if blocks is None:return True
    if not isinstance(blocks,list) or not 1<=len(blocks)<=4:return False
    return all(isinstance(b,dict) and isinstance(b.get('start'),int) and isinstance(b.get('end'),int)
               and 0<=b['start']<b['end']<=len(chunk.text) and chunk.text[b['start']:b['end']]==b.get('text') for b in blocks)
