# Expanded medical RAG verification

Verified locally on 6 November 2026. This is software and source-grounding verification, not clinical validation.

## Root causes and fixes

The old corpus contained only three documents, concentrated on two medicines. Exact medicine/topic gates excluded general health questions. Hash-based embeddings could not represent medical synonyms semantically, and the old generic-medicine clarification ran before useful health retrieval. These constraints caused unnecessary abstention.

The application now uses 36 active official-source documents and 220 active chunks (247 stored chunks including preserved historical versions). The original NHS and HPRA references remain. Sources cover Paracetamol, ibuprofen, cetirizine, amoxicillin, loratadine, omeprazole, metformin, antibiotics, antihistamines, symptoms, prevention, diet, physical activity, general medicine safety and storage. This bounded corpus does not cover all diseases or medicines.

Default retrieval uses local FastEmbed MiniLM ONNX, 384 dimensions, normalized vectors, persisted FAISS window indexes, BM25Plus keyword scores and reciprocal rank fusion. Section-aware parent chunks preserve lists, warning context and provenance; overlapping 160-word embedding windows prevent long sections being truncated to their opening. Exact medicine identity and topic gates remain, including explicit spelling confirmation. Health-topic aliases prevent a new general health question from inheriting a previous medicine. The semantic relevance floor remains 0.30; similarity is not a medical confidence score.

The pipeline retrieves before falling back to a clarification. Selected medical answer blocks are exact source spans, organized under headings and bullets. The validator checks each span's offsets and text against the canonical database chunk, plus source identity, eligibility, expiry and the rendered response. An unknown medicine cannot borrow a generic side-effects article. Lists retain their introductory qualifiers. External LLM providers, when configured, receive the retrieved evidence and may select chunk IDs; the default requires no external LLM and uses grounded extractive answers. Free-form medical synthesis is not enabled.

## Source scope and refresh

`data/reference_catalog.json` contains the expanded bounded source list; `backend/app/knowledge_base/references.py` retains the original three. Every document stores the source URL/title, retrieval time, raw SHA-256, review/publication dates where supplied, source attribution, reuse terms and expiry. Missing source dates remain empty rather than invented. NHS sources expire after 7 days without refresh; other catalog entries after 30. PDF text and product identity are verified before ingestion. Superseded chunks remain for historical citations but are excluded from active retrieval.

NHS material carries OGL attribution. MedlinePlus imports only its public-domain topic summaries, excluding licensed AHFS and A.D.A.M content. WHO fact-sheet imports are bounded educational/private-study extracts, and are excluded in production mode pending applicable permission. HPRA-hosted leaflets retain issuer rights; regulator hosting does not imply a blanket redistribution licence. FDA candidates were excluded when access checks denied retrieval.

Fresh installation and normal refresh:

```powershell
.\.venv\Scripts\python.exe -m pip install -r backend/requirements-lock.txt
.\.venv\Scripts\python.exe scripts/download_embedding_model.py
.\.venv\Scripts\python.exe scripts/import_trusted_references.py
.\.venv\Scripts\python.exe scripts/build_vector_index.py
```

The explicit setup command downloads model assets; normal chat uses local files only. The importer fetches the manifest sources and aborts before committing if verification fails. `--verified-cache` is an operator-only option for the immediately preceding verified downloads (maximum age 24 hours); it is not a chat-time web fallback. Restart the backend after configuration/code changes. The content-keyed index rebuilds when the approved corpus changes. Refresh sources regularly; expired evidence is excluded automatically. Docker now installs the model during image build; Docker itself was not tested on this host.

## Actual results

- Backend: 57 tests passed (including source-span tamper rejection and health-context isolation).
- Frontend: 15 unit tests passed; TypeScript and Vite production build passed.
- Browser: 4 Edge Playwright workflows passed. The expanded workflow submitted 20 different questions through the real chat composer, checked HTTP responses and current corpus fingerprints, compared rendered message IDs, and verified every displayed citation URL and supporting quote. No browser JavaScript errors were recorded. Other workflows covered spelling confirmation, unsupported medicine abstention, safety, follow-ups and existing app pages.
- Real corpus: 30 supported questions plus 3 safety/abstention checks passed. The separate earlier regression suite passed 15/15. FAISS export reopened successfully with 384 dimensions and all 220 active parent chunks.
- Local semantic sanity check: related phrasings cosine 0.699 versus unrelated 0.005; this is a model check, not a clinical metric.

Machine-readable evidence (ignored runtime artifacts): `runtime/expanded-corpus-results.json`, `runtime/expanded-browser-results.json`, `runtime/chat-runtime-results.json`, `runtime/rag-diagnostics.json`, `runtime/trusted-reference-import.json`. They include full answers, real document/chunk IDs, URLs and validation diagnostics. Reproduce with `scripts/verify_expanded_corpus.py`, `scripts/diagnose_rag.py` and `npm run test:e2e` from frontend while both services run.

| Question | Result | Evidence / safety status |
|---|---|---|
| What is paracetamol used for? | Pass | LIMITED_EVIDENCE |
| What are the side effects of paracetamol? | Pass | LIMITED_EVIDENCE |
| How should paracetamol be stored? | Pass | LIMITED_EVIDENCE |
| What is ibuprofen used for? | Pass | LIMITED_EVIDENCE |
| What are the side effects of ibuprofen? | Pass | LIMITED_EVIDENCE |
| Who can take ibuprofen? | Pass | LIMITED_EVIDENCE |
| Does ibuprofen interact with warfarin? | Pass | LIMITED_EVIDENCE |
| What is cetirizine used for? | Pass | LIMITED_EVIDENCE |
| Can cetirizine make me feel sleepy? | Pass | LIMITED_EVIDENCE |
| Who can take cetirizine? | Pass | LIMITED_EVIDENCE |
| How should cetirizine be stored? | Pass | LIMITED_EVIDENCE |
| What dosage information is available for cetirizine? | Pass | LIMITED_EVIDENCE |
| What is amoxicillin used for? | Pass | LIMITED_EVIDENCE |
| What are the side effects of amoxicillin? | Pass | LIMITED_EVIDENCE |
| What are antibiotics? | Pass | LIMITED_EVIDENCE |
| Do antibiotics treat colds? | Pass | LIMITED_EVIDENCE |
| What are the symptoms of dehydration? | Pass | LIMITED_EVIDENCE |
| What causes headaches? | Pass | LIMITED_EVIDENCE |
| How can I prevent a common cold? | Pass | LIMITED_EVIDENCE |
| What is a healthy diet? | Pass | LIMITED_EVIDENCE |
| What are the benefits of physical activity? | Pass | LIMITED_EVIDENCE |
| How should medicines be stored? | Pass | LIMITED_EVIDENCE |
| What are common medicine side effects? | Pass | LIMITED_EVIDENCE |
| What precautions should I take with medicines? | Pass | LIMITED_EVIDENCE |
| What are antihistamines? | Pass | LIMITED_EVIDENCE |
| What are the symptoms of fever? | Pass | LIMITED_EVIDENCE |
| What is omeprazole used for? | Pass | LIMITED_EVIDENCE |
| What is metformin used for? | Pass | LIMITED_EVIDENCE |
| What are the side effects of loratadine? | Pass | LIMITED_EVIDENCE |
| Can cetirizine interact with other medicines? | Pass | LIMITED_EVIDENCE |
| What are the side effects of FictionalDrugQ? | Pass | NO_ADDITIONAL_ALERT |
| Should I double my paracetamol dose? | Pass | NEEDS_PROFESSIONAL_REVIEW |
| I cannot breathe after taking paracetamol | Pass | URGENT_ESCALATION |

Personal doses, treatment changes and diagnosis are not supplied. Emergency escalation and unsupported-evidence abstention remain active. Interaction extracts describe documented cautions; they do not establish that any combination is safe for an individual. Source-derived patient education improves readability while retaining original wording; independent expert review of medical completeness and readability remains outside these software checks.
