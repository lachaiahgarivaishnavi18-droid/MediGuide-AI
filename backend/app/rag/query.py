"""Conservative subject/topic resolution. No fuzzy medication substitution."""
import re
from sqlalchemy import select
from app.models.models import Medication, KnowledgeDocument
from app.knowledge_base.provenance import available

TOPICS = {
    'side_effects':r'side[ -]?effects?|adverse (?:effects?|reactions?)|unwanted (?:effects?|reactions?)|(?:make|makes|feel|feeling).{0,15}(?:sleepy|drowsy|sick|dizzy)',
    'storage':r'\bstor(?:e|age|ing|ed)\b|\brefrigerat|\bkeep\b|\bfridge\b',
    'interactions':r'interact|\btogether\b|\bcombin|\bwith (?:warfarin|alcohol|other medicines)',
    'missed_dose':r'missed|forgot|forget|skipped',
    'precautions':r'precaution|contraindicat|\bwarning|\bavoid|who can|pregnan|breastfeed|watch out|be careful|not (?:take|be used)|before.{0,15}tak',
    'leaflet':r'\bleaflets?\b|patient information',
    'symptoms':r'\bsymptoms?\b|\bsigns?\b',
    'prevention':r'prevent|reduce.{0,25}risk|stop.{0,15}(?:catching|spreading)',
    'causes':r'\bcause[sd]?\b|why (?:do|does)',
    'dosage':r'\bdosage\b|\bdose\b|instructions|how to take',
    'purpose':r'used for|what.{0,30}\bfor\b|\bpurpose\b|\btreat\b|help with|why.{0,30}(?:take|prescribed)|^\s*what (?:is|are)\s+[\w -]+[?.!]*$|tell me about|what does.{0,30}mean|\bbenefits?\b',
}
HEALTH_ALIASES={
 'headache':'headaches','headaches':'headaches','common cold':'common cold','colds':'common cold','cold':'common cold',
 'dehydration':'dehydration','dehydrated':'dehydration','fever':'fever','high temperature':'fever',
 'allergy':'allergies','allergies':'allergies','allergic reaction':'allergies','sore throat':'sore throat',
 'antibiotic':'antibiotics','antibiotics':'antibiotics','antihistamine':'antihistamines','antihistamines':'antihistamines',
 'healthy diet':'healthy diet','balanced diet':'healthy diet','healthy eating':'healthy diet','eat healthily':'healthy diet',
 'physical activity':'physical activity','exercise':'physical activity','staying active':'physical activity',
 'medicine safety':'medicine safety','drug safety':'medicine safety','medication safety':'medicine safety',
 'medicine storage':'medicine storage','medication storage':'medicine storage','store medicines':'medicine storage',
 'patient information leaflet':'patient information leaflets','medication leaflet':'patient information leaflets','medicine leaflet':'patient information leaflets',
 'medicine precautions':'medicine precautions','medication precautions':'medicine precautions',
}


def topic_of(text):
    return next((topic for topic,pattern in TOPICS.items() if re.search(pattern,text,re.I)),None)


def section_topic(section):
    section=' '.join(section.split())
    if re.search(r'side[ -]?effects?|adverse',section,re.I):return 'side_effects'
    if re.search(r'stor|\bkeep\b',section,re.I):return 'storage'
    if re.search(r'missed|forgot|forget|miss a dose',section,re.I):return 'missed_dose'
    if re.search(r'with painkillers|with other|other medicines|interact|food and drink|mixing|cautions with',section,re.I):return 'interactions'
    if re.search(r'leaflet|find out more about your medicine',section,re.I):return 'leaflet'
    if re.search(r'other medicines|interact|food and drink|mixing|cautions with',section,re.I):return 'interactions'
    if re.search(r'what.*used for|what.*is for|\bpurpose\b|^about\b|what (?:is|are)|overview',section,re.I):return 'purpose'
    if re.search(r'need to know|who can|who may|precaution|warning|contraindicat',section,re.I):return 'precautions'
    if re.search(r'missed|forgot|forget|miss a dose',section,re.I):return 'missed_dose'
    if re.search(r'how to take|dose|dosage|how and when',section,re.I):return 'dosage'
    if re.search(r'symptoms|\bsigns\b',section,re.I):return 'symptoms'
    if re.search(r'prevent|reduce.*risk|avoid spreading',section,re.I):return 'prevention'
    if re.search(r'causes|can cause',section,re.I):return 'causes'
    return None


def health_subjects(text):
    found={canonical for alias,canonical in HEALTH_ALIASES.items() if re.search(r'(?<!\w)'+re.escape(alias)+r'(?!\w)',text,re.I)}
    if re.search(r'medicin|medication|drug',text,re.I):
        topic=topic_of(text)
        if topic=='side_effects':found.add('medicine side effects')
        if topic=='storage':found.add('medicine storage')
        if topic=='precautions':found.add('medicine precautions')
        if re.search(r'pharma|safe|safety',text,re.I):found.add('medicine safety')
    if re.search(r'pharmacist|pharmasist',text,re.I):found.add('medicine safety')
    return sorted(found)


def terminology(db):
    aliases = {}
    docs = db.scalars(select(KnowledgeDocument).where(KnowledgeDocument.approved.is_(True), KnowledgeDocument.synthetic.is_(False))).all()
    for doc in docs:
        if not available(doc):
            continue
        for name in [*doc.metadata_json.get("medications", []),*doc.metadata_json.get('mentioned_medications',[])]:
            if name.casefold() not in HEALTH_ALIASES: aliases[name.casefold()] = name.casefold()
        for alias, canonical in doc.metadata_json.get("medication_aliases", {}).items():
            if alias.casefold() in doc.text.casefold() and canonical.casefold() in doc.text.casefold():
                aliases[alias.casefold()] = canonical.casefold()
    for med in db.scalars(select(Medication).join(KnowledgeDocument).where(KnowledgeDocument.approved.is_(True), KnowledgeDocument.synthetic.is_(False))):
        if not available(db.get(KnowledgeDocument,med.document_id)):
            continue
        aliases[med.generic_name.casefold()] = med.generic_name.casefold()
        for brand in med.brand_names:
            aliases[brand.casefold()] = med.generic_name.casefold()
    return aliases


def medicines_in(text, aliases):
    return sorted({canonical for alias, canonical in aliases.items() if re.search(r"(?<!\w)"+re.escape(alias)+r"(?!\w)", text, re.I)})


def explicit_subject(text):
    patterns = [r"(?:side[ -]?effects?|adverse reactions?|storage|purpose|warnings)\s+(?:of|for|from)\s+(.+?)[?.!]*$",
                r"(?:precautions?|contraindications?).{0,60}(?:when using|when taking|using|with|for)\s+(.+?)[?.!]*$",
                r"\bwhat (?:is|are)\s+(.+?)\s+used for", r"\b(?:about|store)\s+([\w-]+)",
                r"\bdoes\s+([\w-]+)\s+(?:have|cause)",r"\bbetween\s+(.+?)[?.!]*$",
                r"^\s*(?:can|could|do|does|will|would|may)\s+(.+?)\s+interact",
                r"^\s*what is\s+((?!.*\bused for\b)[\w -]+)[?.!]*$"]
    for pattern in patterns:
        match = re.search(pattern, text, re.I)
        if match:
            candidate = match.group(1).strip(" ?.!")
            if not re.fullmatch(r"(?:it|this|that|its|the|my|this medicine|that medicine|the medicine)", candidate, re.I):
                return candidate
    return None


def resolve_query(db, query, context=""):
    if is_refusal_echo(query):return query
    aliases = terminology(db)
    medicines = medicines_in(query, aliases)
    subject = explicit_subject(query)
    if medicines or subject or health_subjects(query):
        return query
    if not re.search(r"\bit\b|\bits\b|this medicine|that medicine|^\s*what about\b|^\s*and\b", query, re.I):
        return query
    for previous in reversed(context.splitlines()):
        if is_refusal_echo(previous):continue
        prior = medicines_in(previous, aliases)
        if prior:
            return query + " " + " ".join(prior)
        if explicit_subject(previous):
            break
    return query


def is_refusal_echo(text):
    return bool(re.search(r'i could not find (?:sufficient approved evidence|an approved reference)|i (?:do not|don.t) have an approved passage|that text is a previous no-evidence response',text,re.I))


def query_variants(db,query):
    """Deterministic topic rewrites; no invented medicines or patient facts."""
    if is_refusal_echo(query):return []
    names=medicines_in(query,terminology(db));health=health_subjects(query);topic=topic_of(query)
    subject=explicit_subject(query)
    if not names and subject and not health_subjects(subject) and subject.casefold() not in {'medicine','medicines','medication','medications','drug','drugs'}:
        return [query]
    suffix={'purpose':'uses what is used for','side_effects':'common side effects adverse reactions',
            'precautions':'precautions who cannot take contraindications warnings',
            'interactions':'interactions taking with other medicines painkillers',
            'storage':'storage how to store keep','missed_dose':'if you forget to take miss a dose',
            'leaflet':'patient information leaflet leaflets information about your medicine',
            'symptoms':'symptoms signs','prevention':'prevention reduce risk','causes':'causes',
            'dosage':'dosage how and when to take instructions'}.get(topic,'')
    subject=' and '.join(names) if names else ' '.join(health)
    return list(dict.fromkeys([query,*([subject+' '+suffix] if subject and suffix else [])]))
