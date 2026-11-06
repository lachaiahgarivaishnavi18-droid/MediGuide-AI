import hashlib
import re
from io import BytesIO
from sqlalchemy import select
from fastapi import HTTPException
from bs4 import BeautifulSoup
from app.models.models import KnowledgeDocument, KnowledgeChunk, AuditLog, now

INJECTION = re.compile(r"ignore (?:all |previous |prior )*instructions|system prompt|you are (?:now|chatgpt)|<\|(?:system|assistant)|override (?:the )?safety", re.I)


def extract(data: bytes, extension: str):
    if extension == ".pdf":
        import fitz
        with fitz.open(stream=data, filetype="pdf") as pdf:
            pages = [page.get_text(sort=True) for page in pdf]
            if sum(c.isalpha() for text in pages for c in text) < 10:
                raise ValueError("PDF has no extractable text; OCR is required before indexing")
            text = "\n\n".join(f"Page {i+1}\n\n{page}" for i, page in enumerate(pages))
            return re.sub(r"(?im)^[ \t]*([1-9][.)][ \t]*(?:what|how|possible|side|contents|content|further|before)[^\n]{5,120})[ \t]*$", r"\n\n# \1\n\n", text)
    if extension == ".docx":
        import zipfile
        with zipfile.ZipFile(BytesIO(data)) as archive:
            if sum(item.file_size for item in archive.infolist()) > 40 * 1024 * 1024:
                raise ValueError("Expanded document exceeds size limit")
        from docx import Document
        doc = Document(BytesIO(data))
        return "\n\n".join([p.text for p in doc.paragraphs] + [" | ".join(c.text for c in row.cells) for t in doc.tables for row in t.rows])
    if extension in {".html", ".htm"}:
        soup = BeautifulSoup(data, "html.parser")
        for tag in soup(["script", "style", "nav", "footer"]):
            tag.decompose()
        root = soup.find("main") or soup
        blocks = []
        for tag in root.find_all(["h1", "h2", "h3", "h4", "p", "ul", "ol", "summary"]):
            if tag.find_parent(["ul", "ol"]):
                continue
            value = tag.get_text(" ", strip=True)
            if value:
                blocks.append(("# " if tag.name in {"h1", "h2"} else "") + value)
        return "\n\n".join(blocks) or root.get_text(" ", strip=True)
    if extension in {".txt", ".md"}:
        return data.decode("utf-8-sig")
    raise ValueError("Supported files: PDF, DOCX, HTML, TXT, MD")


def chunk_text(text, size=280, overlap=40):
    if size < 40 or overlap >= size or overlap < 0:
        raise ValueError("Invalid chunk configuration")
    # Never relabel old text with the next heading or detach warning frequencies.
    result, current, section = [], [], "Document"
    protected = False
    for paragraph in re.split(r"\n\s*\n", text):
        paragraph = paragraph.strip()
        if not paragraph:
            continue
        heading = re.fullmatch(r"#{1,6}\s+([^\n]+)", paragraph)
        if heading:
            if current:
                result.append((section, "\n\n".join(current)))
            section = heading.group(1).strip()[:300]
            current = [paragraph]
            protected = bool(re.search(r"side effects|warnings|precautions|contraindications", section, re.I))
            continue
        words = paragraph.split()
        if sum(len(p.split()) for p in current) + len(words) > size and current and not protected:
            result.append((section, "\n\n".join(current)))
            # Keep full trailing paragraphs within the overlap budget.
            current = [current[-1]] if overlap and len(current[-1].split())<=overlap else []
        current.append(paragraph)
    if current:
        result.append((section, "\n\n".join(current)))
    return result


def ingest(db, payload, user_id=None):
    text = payload.text.replace("\x00", "").strip()
    if len(text) < 20:
        raise HTTPException(422, "No usable document text; scanned PDFs require OCR before ingestion")
    if INJECTION.search(text):
        raise HTTPException(422, "Document contains instruction-like content and requires offline review")
    digest = hashlib.sha256(text.encode()).hexdigest()
    existing = db.scalar(select(KnowledgeDocument).where(KnowledgeDocument.content_hash == digest))
    if existing:
        return existing, False
    if payload.source_url and not payload.source_url.startswith("https://"):
        raise HTTPException(422, "Source reference must use HTTPS")
    doc = KnowledgeDocument(title=payload.title, source_name=payload.source_name, source_url=payload.source_url,
                            text=text, content_hash=digest, approved=payload.approved, synthetic=payload.synthetic,
                            metadata_json={**payload.metadata, "retrieved_at":payload.metadata.get("retrieved_at") or now().isoformat(), "document_type": payload.metadata.get("document_type", "text"), "index_version": 2})
    db.add(doc)
    db.flush()
    for i, (section, passage) in enumerate(chunk_text(text)):
        db.add(KnowledgeChunk(document_id=doc.id, text=passage, section=section, ordinal=i))
    db.add(AuditLog(user_id=user_id, action="document_ingested", resource_id=doc.id))
    db.flush()
    return doc, True
