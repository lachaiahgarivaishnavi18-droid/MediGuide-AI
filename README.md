# MediGuide AI

**A knowledge-grounded conversational system for patient education and medication safety information.**

MediGuide helps users inspect medical reference material and prepare questions for healthcare professionals. It is a development application, not a certified or clinically validated medical device. It does not diagnose, prescribe, calculate personal doses, change treatment, or establish that medication combinations are safe.

## What is implemented

- React, TypeScript, Vite, Tailwind, React Router, Axios, Lucide, Markdown, Recharts, and React Flow interface with ten pages.
- FastAPI and Pydantic APIs; SQLAlchemy normalized relational schema; Alembic migration; SQLite development and PostgreSQL configuration.
- Scrypt password hashing, opaque revocable server-side sessions in HttpOnly/SameSite cookies, account ownership checks, administrator authorization, basic request limits, and audit events.
- Admin PDF/DOCX/HTML/text imports, duplicate detection, provenance, paragraph-aware chunks, explicit approval, synthetic exclusion, and a bounded DailyMed SPL connector.
- FAISS vector search, BM25 keyword search, reciprocal rank fusion, metadata filtering, and stored retrieval diagnostics. Offline hashed features work without model downloads; optional Sentence Transformers supplies semantic embeddings.
- Ten modular agents coordinated by LangGraph with an emergency branch, medication review rules, evidence assessment, extractive generation, and mandatory citation validation.
- Persistent conversations, source citations with expandable passages, follow-up context, interaction/duplicate ingredient checks, operational agent traces, account analytics, JSON export, and history deletion.
- Evidence-checked administrative APIs for structured medication records, interactions, and education topics.
- Backend and frontend tests, synthetic regression evaluation, ranking metrics, Docker and Compose configuration, and operational documentation.

## Deliberate boundaries and remaining work

A fresh database starts empty and transparently abstains until trusted references are imported or administrators approve uploaded sources. This workspace has now been populated with three verified official references (27 chunks): NHS paracetamol, NHS ibuprofen, and a regulator-hosted Paracetamol patient leaflet. Run `scripts/import_trusted_references.py` on a fresh installation to populate the same bounded corpus. The included synthetic document contains no medical claims and is excluded from patient answers. There are no fabricated patient records or analytics.

The default answer mode quotes source passages. It does **not** claim to validate the truth of medical statements or their applicability to a person. API/local LLM providers may select passage IDs; free-form generated medical claims are not returned. Readability rewriting, automated medical contradiction detection, claim-level semantic entailment, broad medical NER, cross-encoder reranking, durable shared vector indexing, distributed throttling, password reset/MFA/email verification, comprehensive source connectors, and clinical validation are not implemented. Source freshness and conflicts can be annotated by administrators; relevance scores are never described as clinical certainty. See [safety design](docs/safety_design.md).

Remote ingestion supports DailyMed SPL plus an explicit three-reference NHS/HPRA manifest (not an unrestricted web crawler). It is unit-tested with a mocked official-format response and passed a live API fetch on November 6, 2026; the live content was not stored or approved. MedlinePlus, FDA, WHO, PubMed, and Europe PMC are **not** claimed as integrated connectors. NHS support is limited to the two tested manifest pages. Administrators may import permitted documents with provenance after reviewing usage terms.

## Architecture

```mermaid
flowchart LR
  UI[React workspace] --> API[FastAPI + session authorization]
  API --> G[LangGraph orchestrator]
  G --> Q[Query understanding]
  Q --> S[Safety escalation]
  S -->|urgent| E[Emergency response]
  S -->|education| R[Entities + hybrid retrieval]
  R --> M[Medication safety + evidence evaluation]
  M --> A[Extractive education response]
  A --> V[Citation validation]
  E --> V
  V --> DB[(Conversations + provenance + audit)]
  DB --> UI
```

The system separates presentation, API/authentication, orchestration, retrieval, structured medication safety, relational provenance, and evaluation. See [architecture](docs/architecture.md), [schema](docs/database_schema.md), and [agent workflow](docs/agent_workflow.md).

## Local installation — Windows PowerShell

Use Python **3.12** and Node **22.12+ or 24**, with npm. Run from the repository root; a Python 3.15 installation is not recommended for these ML wheels.

`backend/requirements.txt` declares compatibility ranges; `backend/requirements-lock.txt` records the exact tested baseline and is used by Docker. Use the lock file in place of `requirements.txt` below for a reproducible baseline installation.

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend/requirements.txt
Copy-Item docs/environment.example.txt .env
# Edit .env: set ADMIN_EMAIL and a unique ADMIN_PASSWORD of at least 12 characters.
.\.venv\Scripts\python.exe -m alembic -c backend/alembic.ini upgrade head
.\.venv\Scripts\python.exe scripts/seed_database.py
.\.venv\Scripts\python.exe scripts/import_trusted_references.py
Set-Location frontend
npm ci
Set-Location ..
```

In this workspace, `.venv` and a local npm executable have also been prepared. If `npm` is unavailable:

```powershell
# Only needed on a fresh machine without npm:
.\.venv\Scripts\python.exe scripts/bootstrap_npm.py
Set-Location frontend
node ..\.tools\package\bin\npm-cli.js ci
Set-Location ..
```

Start two terminals from the repository root:

```powershell
# Terminal 1
.\scripts\start-backend.ps1
# Equivalent:
.\.venv\Scripts\python.exe -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000
```

```powershell
# Terminal 2 (uses npm or the local fallback)
.\scripts\start-frontend.ps1
```

Open [MediGuide](http://localhost:5173). Vite proxies `/api` to FastAPI; use the frontend's origin throughout authentication. Backend [OpenAPI docs](http://127.0.0.1:8000/docs), [schema](http://127.0.0.1:8000/openapi.json), and [health](http://127.0.0.1:8000/health) are available. Register your own patient account. No public default credentials are provided. Administrator creation requires environment configuration followed by the seed command.

## General terminal commands

```sh
python3.12 -m venv .venv
.venv/bin/python -m pip install -r backend/requirements.txt
cp docs/environment.example.txt .env
.venv/bin/python -m alembic -c backend/alembic.ini upgrade head
.venv/bin/python scripts/seed_database.py
.venv/bin/python scripts/import_trusted_references.py
.venv/bin/python -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000
# Separate terminal:
cd frontend && npm ci && npm run dev
```

## Environment and database

Configuration is read from `.env` in the repository root. Run backend commands there to keep the SQLite path consistent.

| Variable | Purpose |
|---|---|
| `DATABASE_URL` | `sqlite:///./mediguide.db` or `postgresql+psycopg://user:password@host/database` |
| `CORS_ORIGINS` | Comma-separated exact browser origins; no wildcard credentials |
| `COOKIE_SECURE` | `true` behind production HTTPS; local HTTP uses `false` |
| `ADMIN_EMAIL`, `ADMIN_PASSWORD` | Explicit bootstrap account; never returned by APIs |
| `LLM_PROVIDER` | `extractive` (no credentials), `api`, or `local` |
| `LLM_BASE_URL`, `LLM_MODEL`, `LLM_API_KEY` | OpenAI-compatible selection endpoint; local servers may omit key |
| `EMBEDDING_PROVIDER` | `fastembed` (default, local ONNX MiniLM); `hash` for unit fixtures; optional `sentence-transformers` |
| `EMBEDDING_MODEL` | Embedding model identifier; explicit one-time download required |

To enable semantic embeddings:

```powershell
.\.venv\Scripts\python.exe scripts/download_embedding_model.py
# Default EMBEDDING_PROVIDER=fastembed. Restart backend after changing providers.
```

The optional spaCy dependency is available for future terminology work; current entity extraction uses exact known medication names/brands and dosage-unit patterns. No similarly named medication is automatically substituted.

## Ingestion and source curation

Sign in as an administrator, open Knowledge Base, upload a permitted reference with its issuing source and URL, inspect chunks, then approve it. PDF extraction is text-based; scanned images need external OCR. Source instructions are treated as untrusted data and instruction-like uploads are rejected for offline review. Files are not saved under client-provided paths.

CLI import (pending approval):

```powershell
.\.venv\Scripts\python.exe scripts/ingest_documents.py data/synthetic/catalog.txt --title "Synthetic catalog" --source "Development fixture" --synthetic
.\.venv\Scripts\python.exe scripts/build_vector_index.py
```

The index export writes FAISS and a versioned chunk manifest under ignored `runtime/index` and verifies it by reopening the file. API retrieval caches indexes by content and embedding configuration, applying approval, scope, and expiry gates before ranking. Deleted, withdrawn, or expired evidence cannot bypass those gates. This design prioritizes correctness for a small curated corpus; benchmark and replace with a shared versioned index for large deployments.

For DailyMed, authenticated administrators may call `POST /api/knowledge/dailymed/{SPL_SET_UUID}`. Imports remain pending. Structured records use `POST /api/admin/medications`, `/admin/interactions`, and `/admin/education`; see [API documentation](docs/api_documentation.md). No medication data is inferred from a title alone.

## Tests and evaluation

```powershell
.\.venv\Scripts\python.exe -m pytest -c backend/pytest.ini -q backend/tests
.\.venv\Scripts\python.exe scripts/evaluate_rag.py
Set-Location frontend
npm test
npm run build
npm audit
# With backend and frontend running, uses installed Microsoft Edge by default:
npm run test:e2e
```

Use `node ..\.tools\package\bin\npm-cli.js` in place of `npm` on this host if needed. Synthetic software scenarios are stored in `data/evaluation/cases.json`. Evaluation exports JSON and CSV to `runtime`; it makes no clinical-performance claim. Ranking evaluation accepts an independently annotated dataset:

Browser tests create a reserved `@example.test` synthetic account and remove that exact account in teardown. They exercise desktop/mobile layouts, chat safety, interaction uncertainty, the graph monitor, and analytics; screenshots are saved under ignored `runtime`. On another OS set `E2E_BROWSER=chromium` after installing the corresponding Playwright browser. The tests require the local Python virtual environment for synthetic-account cleanup.

```powershell
.\.venv\Scripts\python.exe scripts/evaluate_rag.py --ranking-dataset path/to/cases.json
```

Each ranking case needs `id`, `query`, `relevant_chunk_ids`, and optional `k`. Precision@K, recall@K, MRR, and NDCG are implemented. Context recall, readable patient summaries, clinical correctness, and claim-level faithfulness require expert-labeled data; they are not synthesized into misleading scores.

`--annotations path/to/annotations.json` computes intent accuracy, entity precision/recall, context relevance/recall, claim faithfulness, unsupported claim rate, citation accuracy/completeness, escalation recall, false reassurance, interaction and duplicate detection accuracy, warning recall, abstention quality, and human-rated relevance/readability/follow-up consistency from externally supplied labels. Missing annotations stay `null`. See `backend/app/evaluation/metrics.py` for the explicit annotation fields; no semantic or clinical labels are inferred automatically.

## Docker

Add `POSTGRES_PASSWORD` to `.env` (use a URL-safe random password for the Compose connection URL), configure an admin, then:

```powershell
docker compose up --build
```

Open [the container frontend](http://localhost:8080). Compose waits for PostgreSQL, runs migrations/seed, then serves the frontend through Nginx. Backend and database ports are not published. Images run under non-root users. This environment may not provide Docker; see [verification](docs/verification.md) for what was actually run. Production requires HTTPS, backups, secret management, clinical governance, and the operational work listed in [deployment](docs/deployment.md).

On a fresh container database, explicitly load the same bounded official-reference corpus with `docker compose exec backend python scripts/import_trusted_references.py`. Compose does not silently fetch and approve arbitrary web content at server startup.

## Repository map

`frontend/src` contains routed screens, typed API models, client integration, styling, and UI tests. `backend/app` separates API, core security, database, models, schemas, agents, RAG, knowledge ingestion, medication safety, services, and evaluation. `backend/migrations` contains the initial schema; `backend/tests` contains integration and safety checks. `scripts` provides seed, import, vector export, startup, and evaluation commands. `docs` explains architecture, APIs, retrieval, safety, deployment, and verification.

## Source and framework references

Implementation follows the [LangGraph graph API](https://reference.langchain.com/python/langgraph/graph/state/StateGraph/compile), [FastAPI security guidance](https://fastapi.tiangolo.com/tutorial/security/oauth2-jwt/), and [DailyMed web services](https://dailymed.nlm.nih.gov/dailymed/app-support-web-services.cfm). Session tokens here are opaque, revocable database sessions rather than JWTs.

## Diagnose missing evidence

See [RAG repair and reproduction guide](docs/rag_debugging.md). Run `.\.venv\Scripts\python.exe scripts/diagnose_rag.py` to verify real imported medicine questions, unknown-medicine abstention, follow-up isolation, citations, and safety. Refresh official references with `scripts/import_trusted_references.py`; NHS references expire from retrieval after seven days, and the product leaflet after thirty days. Expanded citations display source copy dates, scope, and attribution.

See [actual browser-chat repair](docs/chat_runtime_fix.md) for the later spelling, unsupported-prompt and frontend timing fixes, including real captured request/response results. Near medicine spellings now require confirmation rather than silently assuming drug equivalence; starter/follow-up questions come from available sources. SQLite and `.env` paths are anchored to this repository, including when the server is launched from a different working directory.

## Expanded medical references

See [expanded RAG verification](docs/expanded_rag_verification.md) for the source scope, root causes, test results, and refresh procedure. The catalog is in `data/reference_catalog.json`; the original NHS Paracetamol/ibuprofen and HPRA Paracetamol references remain in the importer. Run `scripts/download_embedding_model.py` before a fresh offline setup, then `scripts/import_trusted_references.py` to fetch and verify the bounded sources. Online model access is disabled during normal chat.

## Query and refusal-echo repair

See [actual browser query repair results](docs/rag_query_repair_verification.md) for the final 61-document, 382-chunk corpus, original-versus-expanded query diagnostics, refusal-echo and unknown-medicine safety fixes, exact requested browser questions, calibration results, and modified files.

## Existing backend repository notes

The earlier backend-branch README is retained below; its original commits remain in this repository history.

> # MediGuide-AI
> 
> Backend-only Render deployment source. See [setup guide](docs/render_deployment.md) and `render.yaml`. Select branch `codex/render-backend` in Render. This branch does not publish a frontend; Vercel automatic deployment is disabled for this backend branch.
