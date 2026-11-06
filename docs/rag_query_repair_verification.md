# RAG query repair and actual browser verification

Verified locally on 6 November 2026. This report supersedes the earlier 36-document coverage snapshot. These are software/source-grounding checks, not independent clinical validation.

## Reproduced causes

- The database and retriever never used assistant conversation messages as medical documents: chat context contained only previous user turns. However, pasting the refusal as a new user turn triggered generic medicine-safety retrieval because it mentions a pharmacist. This produced unrelated source-backed information and created the misleading appearance that re-submitting a refusal supplied evidence.
- Missing NHS amoxicillin precautions and cetirizine FAQ sections caused genuine coverage gaps. The FAQ supplies specific general information for the Paracetamol/Cetirizine question; no interaction facts were fabricated.
- Similarity fusion could rank generic "Other side effects" boilerplate above the relevant common-effects section. Generic leaflet questions could retrieve development/licensing text or unrelated medicine-safety material.
- Conversation resolution inherited an earlier medicine for new questions without requiring a clear follow-up reference. Actual browser negative tests exposed a fictional medicine question incorrectly borrowing amoxicillin context. Unknown combinations also required stricter subject parsing.
- The similarity floor was not the primary cause for the reported supported cases. It remains 0.30. The final 20 supported calibration questions and 5 negative cases passed 25/25. Supported cases' best semantic scores ranged from 0.542 to 0.840 with controlled expansions. These values are ranking diagnostics, not medical confidence or a clinical accuracy score.

## Implemented behavior

The original API query is preserved and recorded separately from resolved follow-up text. Controlled query variants expand uses, adverse effects, contraindications, interactions, storage, missed doses, and leaflet questions without inventing medicines, conditions or patient facts. Both original and expanded queries are embedded locally and scored with FAISS and BM25Plus; candidates retain exact medicine, topic, approval, source-expiry and provenance checks before fusion. Diagnostics expose original_query, retrieval_query, query_variants, retrieved count and validation status.

Refusal echoes are recognized as non-medical inputs and retrieve no chunks, with a request to send the original question. They are also skipped when resolving later follow-up context. A new named question cannot inherit a previous medicine. Unknown medicines and mixed known/unknown combinations abstain rather than borrowing another drug's evidence. Missing known-medicine/topic evidence explains which subject is unavailable, and interaction abstention explicitly states that missing evidence establishes neither safety nor danger.

Common-effects questions prefer common-effects sections; serious-effects questions prioritize serious sections and retain an available urgent symptom list. FAQ question boundaries and missed-dose subheadings are preserved. Leaflet answers require actual leaflet content and retain preceding context for pronouns such as "This". Exact source spans, citations and duplicate suppression remain enforced. Personal dose/treatment changes, emergencies and canonical-source validation remain active. The external LLM selection path is still constrained to retrieved chunk IDs; default generation is extractive and does not require an external model API.

The agent monitor now remounts its graph for the selected execution, fixing the initially blank diagram exposed by the full browser regression. No medical safety assertion was removed to pass a test.

## Expanded approved knowledge base

61 active official-source documents, 382 active chunks; 488 stored chunks include historical versions that are excluded from active retrieval. NHS sources now cover Paracetamol, ibuprofen, cetirizine, amoxicillin, azithromycin, metformin, omeprazole, pantoprazole, aspirin (pain-relief and low-dose contexts remain separate sources), colecalciferol/Vitamin D, cyanocobalamin/Vitamin B12, amlodipine and ramipril. Existing NHS, public-domain MedlinePlus summaries, bounded WHO local educational extracts and HPRA-hosted patient leaflets remain.

Canonical NHS redirects were verified and deduplicated before import. Vitamin aliases are accepted only on source pages that explicitly identify them. An initial alias-anchor failure aborted the whole import without modifying the active corpus; it was resolved by restricting the alias declarations rather than weakening validation. Source URLs, titles, retrieval provenance, content hashes, issuer, scope, available update dates and expiry remain in document metadata. Source coverage is bounded: unsupported products, indications, storage conditions or combinations still require a suitable leaflet or professional review. Do not generalize one aspirin formulation or vitamin product's dosing instructions to another.

## Test results

- Backend: 64 tests passed.
- Frontend: 15 unit tests passed; TypeScript and Vite production build passed.
- Edge browser: 5/5 workflows passed. Existing workflows cover app pages, emergency routing, medicine-name confirmation, history/runtime/corpus alignment, source links and citation display. The expanded workflow sends 20 medical questions. The new query-repair workflow sends another 20 questions/echoes through the actual browser composer and POST /api/chat, including all seven exact questions, seven additional medicine-use questions, paraphrases, a missed-dose question and two unknown-medicine negatives. HTTP status, original request text, diagnostics, displayed message ID, evidence outcome, supporting quotations and citation links are checked. No browser JavaScript errors were recorded.
- Real corpus answer/safety regression: 33/33 passed; original regression: 15/15 passed.
- Retrieval calibration: 25/25 passed with the unchanged 0.30 floor.
- Exported FAISS reopened successfully: 382 parent passages, 384 dimensions. Dependency check reported no broken requirements.

The browser initially caught both the unknown-context leak and the blank monitor graph; both were fixed and the complete browser suite was rerun. Results below are from the final successful run.

| Exact question submitted through browser chat | Outcome | Citation links |
|---|---|---|
| What are the common side effects of paracetamol? | LIMITED_EVIDENCE | [NHS source](https://www.nhs.uk/medicines/paracetamol-for-adults/) |
| What is ibuprofen used for? | LIMITED_EVIDENCE | [NHS source](https://www.nhs.uk/medicines/ibuprofen-for-adults/) |
| How can I understand my medication leaflet? | LIMITED_EVIDENCE | [NHS source](https://www.nhs.uk/tests-and-treatments/medicines-information/) |
| What are the side effects of cetirizine? | LIMITED_EVIDENCE | [NHS source](https://www.nhs.uk/medicines/cetirizine/side-effects-of-cetirizine/) |
| Can paracetamol and cetirizine interact? | LIMITED_EVIDENCE | [NHS source](https://www.nhs.uk/medicines/cetirizine/common-questions-about-cetirizine/) |
| What precautions should I take when using amoxicillin? | LIMITED_EVIDENCE | [NHS source](https://www.nhs.uk/medicines/amoxicillin/who-can-and-cannot-take-amoxicillin/) |
| What is metformin used for? | LIMITED_EVIDENCE | [NHS source](https://www.nhs.uk/medicines/metformin/) |

Pasting the original refusal produced INSUFFICIENT_EVIDENCE, zero retrieved passages, zero citations, an empty rewrite list, and a request for the original medical question. Unknown medicines/combinations also produced zero citations. They were not marked safe.

## Evidence artifacts and reproduction

- `runtime/query-repair-browser-results.json`: complete actual API answers, citation URLs and supporting quotations, original and rewritten queries, current runtime/corpus identity, evidence/safety outcomes for the 20-case new browser workflow. Read as UTF-8.
- `runtime/expanded-browser-results.json`: other 20-case coverage workflow.
- `runtime/retrieval-calibration.json`: 25-case relevance/calibration details and similarity scores.
- `runtime/expanded-corpus-results.json`, `runtime/rag-diagnostics.json`: complete source-grounded answer regressions.
- `runtime/trusted-reference-import.json`: per-source verification and active chunk counts.

```powershell
.\.venv\Scripts\python.exe -m pytest backend/tests -q
.\.venv\Scripts\python.exe scripts/calibrate_retrieval.py
.\.venv\Scripts\python.exe scripts/verify_expanded_corpus.py
.\.venv\Scripts\python.exe scripts/diagnose_rag.py
# Frontend directory, while backend/frontend run:
node ..\.tools\package\bin\npm-cli.js test
node ..\.tools\package\bin\npm-cli.js run build
node ..\.tools\package\bin\npm-cli.js run test:e2e
```

Normal source refresh uses `scripts/import_trusted_references.py` (online bounded fetch). The setup import here used immediately verified local downloads via `--verified-cache`; this is not a chat-time fallback. References expire unless refreshed, and commercial/production WHO reuse restrictions remain unchanged. Existing saved messages retain their historical responses; new questions use the corrected pipeline.

## Files modified in this repair

- `backend/app/rag/query.py`
- `backend/app/rag/retrieval.py`
- `backend/app/knowledge_base/references.py`
- `backend/app/agents/knowledge_retrieval.py`
- `backend/app/agents/query_understanding.py`
- `backend/app/agents/response_generation.py`
- `backend/app/agents/citation_validation.py`
- `backend/app/services/answer_plan.py`
- `backend/app/api/routes.py`
- `data/reference_catalog.json`
- `frontend/src/App.tsx`
- `backend/tests/test_chat_functionality.py`
- `backend/tests/test_query_repair.py`
- `frontend/e2e/query-repair.spec.ts`
- `scripts/calibrate_retrieval.py`
- `docs/rag_query_repair_verification.md`
- `README.md`
