# Relational schema

The initial Alembic revision creates normalized tables with UUID primary keys and created/updated timestamps. Source/chunk, medication terminology, user ownership, and execution relationships use foreign keys. User email, role name, ingredient name, source content digest, session hash, and setting key are unique. Document/ordinal and medication/ingredient pairs have unique constraints.

| Tables | Purpose |
|---|---|
| users, roles, session_tokens | Identity, role authorization, revocable expiring sessions |
| conversations, messages | Account-owned history and structured answer snapshots |
| medications, active_ingredients, medication_ingredients | Curated drug names and ingredient relationships |
| medication_warnings, medication_interactions | Source-chunk-backed structured safety records |
| education_topics | Approved document categories |
| knowledge_documents, knowledge_chunks | Source text, provenance, approval, chunk identities |
| retrieval_logs, agent_executions, safety_alerts, citation_records | Evidence references and operational results |
| feedback, audit_logs, system_settings | Supporting storage; feedback/settings administration APIs are not included |

Conversation deletion cascades to messages, executions, retrieval logs, alerts, feedback, and citation records. Audit records retain event identifiers without chat text. Source deletion cascades to chunks, medication records, and citation relationships; historical message snapshots may still contain their originally quoted evidence. Review retention policies before operating with real data. SQLite foreign keys are enabled explicitly. PostgreSQL is selected by connection URL; no vector embeddings are stored in relational columns.

The migration is a frozen set of Alembic operations. Schema changes require a new revision. Never use table creation as a replacement for migration in production. Backup before applying a revision; validate downgrade on a disposable database.
