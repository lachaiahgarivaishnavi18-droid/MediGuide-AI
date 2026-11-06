import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
from sqlalchemy import select
from app.database.session import SessionLocal
from app.models.models import Role, User
from app.core.security import hash_password
from app.core.config import settings


def seed():
    with SessionLocal() as db:
        for name in ("patient", "admin"):
            if not db.scalar(select(Role).where(Role.name == name)):
                db.add(Role(name=name))
        db.flush()
        if settings.admin_email and settings.admin_password:
            if len(settings.admin_password) < 12:
                raise ValueError("ADMIN_PASSWORD must be at least 12 characters")
            email = settings.admin_email.strip().lower()
            if not db.scalar(select(User).where(User.email == email)):
                role = db.scalar(select(Role).where(Role.name == "admin"))
                db.add(User(email=email, name="Knowledge administrator", role_id=role.id, password_hash=hash_password(settings.admin_password)))
        db.commit()
    print("Roles seeded. Admin created only if configured. No medical facts or patient records fabricated.")


if __name__ == "__main__":
    seed()
