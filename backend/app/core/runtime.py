import hashlib
import os
import uuid
from pathlib import Path

root=Path(__file__).resolve().parents[1]
digest=hashlib.sha256()
for path in sorted(root.rglob('*.py')):
    digest.update(str(path.relative_to(root)).encode());digest.update(path.read_bytes())
RUNTIME={'runtime_id':uuid.uuid4().hex[:12],'build_id':digest.hexdigest()[:12],'backend_pid':os.getpid()}
