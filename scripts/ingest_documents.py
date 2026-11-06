"""Ingest a local reference; human approval is a separate authenticated API operation."""
import argparse
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"backend"))
from app.database.session import SessionLocal
from app.knowledge_base.ingestion import extract, ingest
from app.schemas.api import IngestRequest

parser=argparse.ArgumentParser()
parser.add_argument("file",type=Path)
parser.add_argument("--title",required=True)
parser.add_argument("--source",required=True)
parser.add_argument("--url",default="")
parser.add_argument("--synthetic",action="store_true")
args=parser.parse_args()
if args.file.stat().st_size>10*1024*1024:
    parser.error("File exceeds 10 MB")
text=extract(args.file.read_bytes(),args.file.suffix.lower())
with SessionLocal() as db:
    doc,created=ingest(db,IngestRequest(title=args.title,source_name=args.source,source_url=args.url,text=text,synthetic=args.synthetic,metadata={"file_reference":args.file.name,"document_type":args.file.suffix.lower()}))
    db.commit()
    print({"document_id":doc.id,"created":created,"approved":doc.approved})
