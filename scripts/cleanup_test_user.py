"""Remove only the exact reserved synthetic browser-test account supplied by the test."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'backend'))
from sqlalchemy import select
from app.database.session import SessionLocal
from app.models.models import User

email=sys.argv[1]
if not email.startswith('e2e-') or not email.endswith('@example.test'):
    raise ValueError('Only reserved e2e synthetic accounts may be cleaned up')
with SessionLocal() as db:
    user=db.scalar(select(User).where(User.email==email))
    if user:
        db.delete(user);db.commit()
