"""Versioned official-source catalog and content scopes; no arbitrary URL loading."""
import json
from app.core.config import PROJECT_ROOT


def expanded_references():
    records=json.loads((PROJECT_ROOT/'data/reference_catalog.json').read_text(encoding='utf-8'))
    result=[]
    for record in records:
        source=record.get('source','NHS')
        result.append({'format':'html','aliases':{},'scope':'General patient education; country and product context apply',
                       'refresh_days':7 if source=='NHS' else 30,'issuer':{'NHS':'Department of Health and Social Care','MedlinePlus':'National Library of Medicine, NIH','WHO':'World Health Organization','FDA':'U.S. Food and Drug Administration'}.get(source,'Leaflet issuer; regulator-hosted reference'),
                       'medicine':'','source':source,**record})
    return result
