from datetime import datetime, timezone


def available(doc):
    if not doc.approved or doc.synthetic:
        return False
    if doc.metadata_json.get('noncommercial_only'):
        from app.core.config import settings
        if settings.environment=='production':return False
    expires = doc.metadata_json.get("expires_at")
    if expires:
        try:
            return datetime.fromisoformat(expires).replace(tzinfo=timezone.utc) > datetime.now(timezone.utc)
        except (ValueError,TypeError):
            return False
    return True


def active_chunk(chunk,doc):
    active=doc.metadata_json.get('active_chunk_ids')
    return active is None or chunk.id in active
