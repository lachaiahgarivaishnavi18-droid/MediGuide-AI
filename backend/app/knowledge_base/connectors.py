"""Bounded DailyMed connector. No arbitrary URL fetching or redirect following."""
import re
import httpx
from defusedxml import ElementTree


def fetch_dailymed(set_id: str):
    if not re.fullmatch(r"[0-9a-fA-F-]{36}", set_id):
        raise ValueError("A DailyMed SPL set UUID is required")
    url = f"https://dailymed.nlm.nih.gov/dailymed/services/v2/spls/{set_id}.xml"
    with httpx.Client(timeout=20, follow_redirects=False) as client:
        with client.stream("GET", url) as response:
            response.raise_for_status()
            data = bytearray()
            for block in response.iter_bytes():
                data.extend(block)
                if len(data) > 10 * 1024 * 1024:
                    raise ValueError("Remote document exceeds size limit")
    root = ElementTree.fromstring(data)
    ns = {"h": "urn:hl7-org:v3"}
    sections = []
    for section in root.findall(".//h:section", ns):
        title = section.find("h:title", ns)
        body = section.find("h:text", ns)
        if body is not None:
            sections.append("# " + (" ".join(title.itertext()) if title is not None else "Label section") + "\n\n" + " ".join(body.itertext()))
    if not sections:
        raise ValueError("No label sections found")
    return {"title": f"DailyMed label {set_id}", "source_name": "DailyMed", "source_url": f"https://dailymed.nlm.nih.gov/dailymed/drugInfo.cfm?setid={set_id}", "text": "\n\n".join(sections), "approved": False, "metadata": {"document_type": "SPL", "issuer": "Label issuer via DailyMed", "license": "Review label usage terms", "set_id": set_id}}
