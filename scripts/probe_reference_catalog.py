"""Check the bounded candidate catalog before approving parsed source content."""
import sys,json,time
from pathlib import Path
from urllib.robotparser import RobotFileParser
from urllib.parse import urlsplit
import httpx
from bs4 import BeautifulSoup

root=Path(__file__).resolve().parents[1]
catalog=json.loads((root/'data/reference_catalog.json').read_text(encoding='utf-8'))
destination=root/'runtime/catalog-probe';destination.mkdir(parents=True,exist_ok=True)
report=[];policies={}
with httpx.Client(timeout=25,follow_redirects=False,headers={'User-Agent':'MediGuideAI/0.2 local-education reference-check'}) as client:
 for spec in catalog:
  item={'id':spec['id'],'url':spec['url']}
  try:
   parts=urlsplit(spec['url']);origin=f'{parts.scheme}://{parts.netloc}'
   if origin not in policies:
    response=client.get(origin+'/robots.txt');policy=RobotFileParser();policy.parse(response.text.splitlines() if response.status_code==200 else [])
    if response.status_code in {401,403,429} or response.status_code>=500:raise ValueError('Robots access restriction')
    policies[origin]=policy
   if not policies[origin].can_fetch('*',spec['url']):raise ValueError('Robots disallows document')
   response=client.get(spec['url']);item.update(status=response.status_code,redirect=response.headers.get('location'),bytes=len(response.content))
   if response.status_code==200:
    suffix=spec.get('format','html');(destination/(spec['id']+'.'+suffix)).write_bytes(response.content)
    if suffix=='html':
     soup=BeautifulSoup(response.content,'html.parser');item['title']=soup.h1.get_text(' ',strip=True) if soup.h1 else None
     item['headings']=[h.get_text(' ',strip=True) for h in soup.select('main h2, main h3, .sf-detail-body-wrapper h2')][:30]
   print(json.dumps(item,ensure_ascii=True),flush=True)
  except Exception as exc:item['error']=str(exc);print(json.dumps(item),flush=True)
  report.append(item);time.sleep(.2)
(destination/'report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
