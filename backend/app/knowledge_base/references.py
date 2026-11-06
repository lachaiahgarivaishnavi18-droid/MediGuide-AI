"""Small explicit public-reference manifest, never an unrestricted web scraper."""
import hashlib
import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlsplit
from urllib.robotparser import RobotFileParser
import httpx
from bs4 import BeautifulSoup
from app.knowledge_base.ingestion import extract
from app.schemas.api import IngestRequest
from app.knowledge_base.catalog import expanded_references

OGL = "https://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/"
REFERENCES = [
    {"id":"nhs-paracetamol", "url":"https://www.nhs.uk/medicines/paracetamol-for-adults/", "format":"html", "medicine":"paracetamol", "aliases":{"panadol":"paracetamol"}, "issuer":"Department of Health and Social Care", "source":"NHS", "scope":"Adults aged 18 or over; England", "refresh_days":7},
    {"id":"nhs-ibuprofen", "url":"https://www.nhs.uk/medicines/ibuprofen-for-adults/", "format":"html", "medicine":"ibuprofen", "aliases":{"nurofen":"ibuprofen"}, "issuer":"Department of Health and Social Care", "source":"NHS", "scope":"Adults aged 18 or over; England; product/formulation matters", "refresh_days":7},
    {"id":"hpra-paracetamol", "url":"https://assets.hpra.ie/products/Human/22017/7871bfd4-8dbb-41a3-aa04-117483654ca6.pdf", "format":"pdf", "medicine":"paracetamol", "aliases":{}, "issuer":"Haleon Ireland Limited", "source":"HPRA-hosted patient leaflet", "scope":"Paracetamol 500mg film-coated tablets; PA 678/150/001; Ireland", "refresh_days":30},
]
REFERENCES[0]['primary']=True
REFERENCES[1]['primary']=True
REFERENCES[2]['product']='PA 678/150/001'
REFERENCES += expanded_references()
AGENT = "MediGuideAI/0.1 public-reference-import"


def download_reference(client, spec, policies):
    if spec not in REFERENCES:
        raise ValueError("Only manifest references may be fetched")
    url = spec["url"]
    parts = urlsplit(url)
    origin = f"{parts.scheme}://{parts.netloc}"
    if origin not in policies:
        robots = client.get(origin+"/robots.txt", headers={"User-Agent":AGENT})
        if robots.status_code in {401,403,429} or robots.status_code >= 500:
            raise ValueError("Source robots policy unavailable or access restricted")
        policy = RobotFileParser()
        policy.parse(robots.text.splitlines() if robots.status_code == 200 else [])
        policies[origin] = policy
    if not policies[origin].can_fetch(AGENT, url):
        raise ValueError("Source robots policy disallows this reference")
    with client.stream("GET", url, headers={"User-Agent":AGENT}) as response:
        response.raise_for_status()
        data = bytearray()
        for block in response.iter_bytes():
            data.extend(block)
            if len(data) > 10*1024*1024:
                raise ValueError("Reference exceeds 10 MB")
    return bytes(data)


def _blocks(root, title, medline=False):
    parts=['# '+title]
    for tag in root.find_all(['h2','h3','h4','p','ul','ol','summary']):
        if tag.find_parent(['ul','ol']):continue
        if tag.name in {'h2','h3','h4'} and tag.get_text(' ',strip=True).startswith(('More in ','Page last reviewed')):break
        if tag.name in {'h2','h3','h4'} and tag.get_text(' ',strip=True)=='Contents':continue
        if tag.name in {'ul','ol'}:
            value='\n'.join('- '+item.get_text(' ',strip=True) for item in tag.find_all('li',recursive=False))
        else:value=tag.get_text(' ',strip=True)
        if value:parts.append(('# ' if tag.name in {'h2','summary'} or medline and tag.name=='h3' or tag.name in {'h3','h4'} and re.search(r'forget|miss a dose',value,re.I) else '')+value)
    return '\n\n'.join(parts)


def parse_reference(spec, data, retrieved_at=None):
    stamp=retrieved_at or datetime.now(timezone.utc)
    source=spec['source'];medicine=spec.get('medicine','')
    metadata={'reference_id':spec['id'],'document_type':spec['format'],'medications':[medicine] if medicine else [],
              'health_topics':spec.get('health_topics',[]),'medication_aliases':spec.get('aliases',{}),
              'issuer':spec['issuer'],'population_scope':spec['scope'],'retrieved_at':stamp.isoformat(),
              'expires_at':(stamp+timedelta(days=spec['refresh_days'])).isoformat(),
              'download_sha256':hashlib.sha256(data).hexdigest(),'chunker_version':3,'parser_version':4,
              'curation':'Official-origin scoped import requested by operator; not clinical certification'}
    title=''
    if spec['format']=='pdf':
        if not data.startswith(b'%PDF'):raise ValueError('Expected PDF content')
        text=extract(data,'.pdf')
        product=spec.get('product','PA 678/150/001')
        if product.casefold() not in text.casefold():raise ValueError('PDF product identity missing; review required')
        import fitz
        with fitz.open(stream=data,filetype='pdf') as pdf:metadata['page_count']=len(pdf)
        title=spec.get('product','Paracetamol 500mg Film-coated tablets')+' — patient leaflet'
        if spec['id']=='hpra-paracetamol':title='Paracetamol 500mg Film-coated tablets — patient leaflet (PA 678/150/001)'
        revision=re.search(r'(?:last revised|revised|last updated)\s*(?:in|on|:)??\s+([A-Za-z]+\s+20\d{2}|[0-9/.-]+)',text,re.I)
        metadata.update(source_updated_at=revision.group(1) if revision else '',license='Leaflet issuer retains rights; local reference copy; no redistribution licence asserted',
                        attribution='Official product leaflet hosted by HPRA; product-specific information.')
    else:
        soup=BeautifulSoup(data,'html.parser')
        if not soup.h1:raise ValueError('Missing source title; structure review required')
        title=soup.h1.get_text(' ',strip=True)
        if source=='MedlinePlus':
            root=soup.select_one('#topic-summary')
            if not root:raise ValueError('NLM public-domain topic summary unavailable; licensed content was not substituted')
            text=_blocks(root,title,medline=True)
            date=soup.find('meta',attrs={'name':'DC.Date.Modified'})
            metadata.update(source_updated_at=date.get('content','') if date else '',license='U.S. government public-domain health-topic summary only',
                license_url='https://medlineplus.gov/about/using/usingcontent/',attribution='Source: MedlinePlus, National Library of Medicine. Only the public-domain topic summary is reproduced.')
        elif source=='WHO':
            root=soup.select_one('.sf-detail-body-wrapper')
            if not root:raise ValueError('WHO fact-sheet body unavailable')
            parts=['# '+title];enabled=False
            for tag in root.find_all(['h2','p','ul','ol']):
                if tag.find_parent(['ul','ol']):continue
                if tag.name=='h2':enabled=tag.get_text(' ',strip=True) in spec.get('extract_sections',['Key facts'])
                if enabled:
                    value=tag.get_text(' ',strip=True)
                    if tag.name in {'ul','ol'}:value='\n'.join('- '+li.get_text(' ',strip=True) for li in tag.find_all('li',recursive=False))
                    parts.append(('# ' if tag.name=='h2' else '')+value)
            text='\n\n'.join(parts)
            date=soup.find('time') or soup.select_one('.date, .sf-item-publication-date')
            metadata.update(source_updated_at=(date.get('datetime') or date.get_text(' ',strip=True)) if date else '',
                license='WHO website educational/private-study extracts; non-commercial local use; commercial reuse requires permissions review',
                license_url='https://www.who.int/about/policies/terms-of-use',noncommercial_only=True,
                attribution='Source: World Health Organization. Selected fact-sheet extracts for educational/private study; no WHO endorsement.')
        else:
            root=soup.find('main')
            if not root:raise ValueError('Source main content missing')
            root=BeautifulSoup(str(root),'html.parser')
            for tag in root.select('nav, aside, script, style, .nhsuk-contents-list, .nhsuk-pagination, .nhsuk-related-nav, .related-nav, .field--name-field-related-links'):tag.decompose()
            text=_blocks(root,title)
            if source=='NHS':
                metadata.update(preferred_general_education=True,license='Open Government Licence v3.0; NHS terms apply',license_url=OGL,
                    terms_url='https://www.nhs.uk/our-policies/terms-and-conditions/',attribution=f"Information from the NHS website, as at {stamp.strftime('%d%m%y')}.")
                for script in soup.find_all('script',type='application/ld+json'):
                    try:
                        info=json.loads(script.string or script.get_text())
                        if isinstance(info,dict) and info.get('@type')=='MedicalWebPage':
                            metadata['source_updated_at']=info.get('dateModified','');metadata['source_review_dates']=info.get('lastReviewed',[])
                    except (ValueError,TypeError):continue
                mentions=[]
                for link in root.select('a[href^="/medicines/"]'):
                    name=link.get_text(' ',strip=True).casefold()
                    if re.fullmatch(r'[a-z][a-z -]{2,29}',name) and name in text.casefold():mentions.append(name)
                metadata['mentioned_medications']=sorted(set(mentions))
            elif source=='FDA':
                # Restrict federal content to the article body where available.
                article=soup.select_one('.field--name-body')
                if article:text=_blocks(article,title)
                date=soup.find('time')
                metadata.update(source_updated_at=(date.get('datetime') or date.get_text(' ',strip=True)) if date else '',
                    license='U.S. government patient-education text; third-party materials excluded',license_url='https://www.fda.gov/about-fda/contact-fda/website-policies',
                    attribution='Source: U.S. Food and Drug Administration.')
    expected=spec.get('expected') or medicine or title
    if expected.casefold() not in text.casefold():raise ValueError('Expected reference identity missing')
    for alias,canonical in metadata['medication_aliases'].items():
        if alias.casefold() not in text.casefold() or canonical.casefold() not in text.casefold():raise ValueError('Alias lacks a source anchor')
    return IngestRequest(title=title,source_name=source,source_url=spec['url'],text=text,approved=True,synthetic=False,metadata=metadata)
