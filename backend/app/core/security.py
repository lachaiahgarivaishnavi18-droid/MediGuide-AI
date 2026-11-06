import hashlib
import hmac
import secrets
from datetime import timedelta, timezone
from fastapi import Depends, HTTPException, Request
from sqlalchemy import select
from app.database.session import get_db
from app.models.models import User, Role, SessionToken, now


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    digest = hashlib.scrypt(password.encode(), salt=salt.encode(), n=16384, r=8, p=1).hex()
    return f"scrypt${salt}${digest}"


def verify_password(password, stored):
    _, salt, expected = stored.split("$")
    actual = hashlib.scrypt(password.encode(), salt=salt.encode(), n=16384, r=8, p=1).hex()
    return hmac.compare_digest(actual, expected)


def digest_token(token):
    return hashlib.sha256(token.encode()).hexdigest()


def current_user(request: Request, db=Depends(get_db)):
    token = request.cookies.get("mediguide_session", "")
    session = db.scalar(select(SessionToken).where(SessionToken.token_hash == digest_token(token)))
    if not session or session.expires_at.replace(tzinfo=timezone.utc) < now():
        raise HTTPException(401, "Please sign in")
    # Cross-origin form submissions must not mutate authenticated state.
    if request.method not in {"GET", "HEAD", "OPTIONS"}:
        from app.core.config import settings
        origin = request.headers.get("origin")
        if origin and origin not in settings.cors_origins.split(","):
            raise HTTPException(403, "Untrusted request origin")
    return db.get(User, session.user_id)


def admin_user(user=Depends(current_user), db=Depends(get_db)):
    if db.get(Role, user.role_id).name != "admin":
        raise HTTPException(403, "Administrator access required")
    return user


def public_user(db, user):
    return {"id": user.id, "email": user.email, "name": user.name, "role": db.get(Role, user.role_id).name, "preferences": user.preferences}
