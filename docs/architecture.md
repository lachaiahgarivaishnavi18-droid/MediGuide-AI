# Architecture

The React workspace talks to same-origin `/api` routes through Vite locally or Nginx in Compose. FastAPI authenticates a database-backed opaque session, then checks account ownership or administrator role before performing work. The service never accepts a client-selected role.

LangGraph invokes typed state nodes. State contains the current query, bounded earlier user context, selected evidence, statuses, and operational timings. The database session remains inside the request; it is never persisted in a model prompt. Emergency recognition routes directly to evidence assessment and emergency generation, followed by citation validation. Ordinary routing includes entity recognition, retrieval, medication checks, source assessment, extractive education, and response validation.

SQLAlchemy stores accounts, conversations, source text and provenance, structured terminology, medication facts, citations, execution metadata, and audit events. Foreign keys and cascades prevent orphaned conversation telemetry. Retrieval reads approved nonsynthetic documents, embeds chunks, and fuses FAISS and BM25 rankings. The current small-corpus implementation rebuilds per query to avoid index staleness; it is not designed for a national-scale corpus.

There are no patient vitals, verified clinical records, clinical predictions, or hidden reasoning logs. Per-account analytics report observed service activity only. Real medical source approval must be performed by a qualified curator; an administrator flag is an access-control mechanism, not a clinical certification.
