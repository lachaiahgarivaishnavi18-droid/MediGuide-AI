# API reference

The generated `/docs` and `/openapi.json` are authoritative for parameter schemas. All `/api` routes except authentication and system status require an active HttpOnly session cookie. Patient requests are scoped to the authenticated account; user IDs supplied by clients are not trusted. Administrative routes return 403 for ordinary users. Missing or other-account private resources return 404.

Both `http://localhost:5173` and `http://127.0.0.1:5173` are included in development origins so the printed Vite URL and the README URL support browser mutations. Production must explicitly configure its exact origin.

| Group | Routes |
|---|---|
| Auth | POST `/auth/register`, `/auth/login`, `/auth/logout`; GET/PATCH `/auth/me` |
| Conversations | POST/GET/DELETE `/conversations`; GET/DELETE `/conversations/{id}` |
| Chat | POST `/chat`, `/chat/stream`; GET `/chat/{conversation_id}/messages` |
| Medication | GET `/medications`, `/medications/search?q=`, `/medications/{id}`, `/medications/{id}/safety` |
| Interactions | POST `/interactions/check`; GET `/interactions/{id}` |
| Education | GET `/education`, `/education/search?q=&category=`, `/education/{id}` |
| Knowledge admin | GET/POST ingestion/upload, GET/PATCH/DELETE `/knowledge/documents/{id}`; POST `/knowledge/retrieve`, `/knowledge/diagnose`; POST `/knowledge/dailymed/{set_id}` |
| Knowledge status | GET `/knowledge/status` |
| Structured curation admin | POST `/admin/medications`, `/admin/interactions`, `/admin/education` |
| Agents | POST `/agents/run`; GET `/agents/status`, `/agents/executions`, `/agents/executions/{id}` |
| Analytics | GET `/analytics/overview`, `/analytics/queries`, `/analytics/retrieval`, `/analytics/safety` |
| System | GET `/health` (outside API prefix), `/system/status` |

List endpoints bound results; conversations/documents accept `offset` and `limit` (1–100). Medication search supports those parameters. Current education/execution endpoints cap at 100. Authentication and chat requests have process-local rate limits; these must become distributed before multi-worker operation. Validation uses 422, unauthenticated 401, unauthorized 403, unknown private resources 404, duplicates 409, oversized imports 413, rate limits 429, upstream agent failures 503.

Chat body: `{"query":"Your question", "conversation_id":null}`. Responses contain conversation/message IDs, answer, intent, evidence/safety statuses, validated citations, safety alerts, suggestions, and limitations. Follow-ups reuse the conversation ID. SSE returns one validated `answer` event after completion.

`GET /api/chat/suggestions` returns question strings derived from approved source sections. Responses may include `clarification` with `kind`, `input_name`, and source-derived `candidates` containing `medicine` and `suggested_query`. A suggested spelling is never automatically treated as a verified medication identity; the frontend requires the user's explicit confirmation before posting the suggested query. Clarification responses contain no medical citations/claims. Operational `diagnostics` contain runtime/build IDs, corpus fingerprint, resolved retrieval query, passage count, and validation outcome. `/api/system/status` exposes the current runtime/build identity; `/api/knowledge/status` includes the corpus fingerprint. No credentials or private reasoning are returned.

Text ingestion body: `{"title":"Reference", "source_name":"Issuing organization", "source_url":"https://...", "text":"Source text", "approved":false, "synthetic":false, "metadata":{"updated_date":"YYYY-MM-DD", "license":"Reviewed usage terms"}}`. Upload uses multipart `file`, `title`, `source_name`, and optional `source_url`; all uploads start unapproved. Review chunk text with GET detail; approve with PATCH `{"approved":true}`.

Medication curation body:

Upload also accepts an optional comma-separated `medications` field. Each tag must occur in the extracted document. Tags scope medicine retrieval but never approve the document. Empty/scanned PDFs return an OCR-required 422 error instead of being marked indexed. The diagnostic route accepts the same body as retrieval and reports available/pending/expired document and chunk counts, embedding dimensions/norm, subject/topic resolution, and actual scored passages; it is administrator-only.

```json
{
  "document_id": "approved-source-uuid",
  "generic_name": "Exact name in source",
  "brand_names": [],
  "active_ingredients": ["Exact ingredient in source"],
  "drug_class": "",
  "facts": [{"field":"storage", "text":"Exact source excerpt", "chunk_id":"existing-chunk-uuid"}]
}
```

Every name and ingredient must occur in the approved source. Each fact must exactly match its cited chunk. Warning fields are `warnings`, `precautions`, `contraindications`, and `serious_warnings`. A human must verify that the excerpt refers to the right product/formulation and that ingredient normalization is valid.

Interaction curation body: `{"medication_a":"uuid", "medication_b":"uuid", "chunk_id":"uuid", "text":"Exact documented interaction excerpt"}`. Both names must appear in the passage. Co-occurrence is not clinical entailment; administrator review is mandatory. Education curation body: `{"document_id":"uuid", "category":"general"}` (also `disease` or `medication`). These operations are available through OpenAPI; the current admin screen focuses on document review and retrieval.
