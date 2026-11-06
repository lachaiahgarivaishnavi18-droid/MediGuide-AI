# Actual chatbot runtime repair

The earlier exact-spelling tests were too narrow. Inspection of the failed requests found `paracetomal`, `pharacetemol`, and `paracetemol`, alongside built-in questions such as “What should I ask my pharmacist?” and generic medication-storage/leaflet questions. Those calls retrieved **zero passages** and their abstentions passed validation. The citation gate was not discarding valid evidence in those requests. The three documents and 27 chunks were available in the running database.

## Implemented changes

- Added source-terminology-derived spelling **suggestions requiring an explicit user click**. Similar names are never silently assumed equivalent. A spelling question now receives a name-confirmation card. Only the confirmed question retrieves medicine facts and citations. Unknown medicines without a suitable confirmed identity still abstain.
- Added medicine/topic clarification for generic requests that cannot be answered from this medicine-specific corpus. The choices are generated from actual available source sections, not invented medical answers.
- Replaced dead starter/follow-up prompts with questions generated from available approved medicine/topic pairs. The legacy unsupported prompts are no longer offered by the new chat interface.
- Moved the chat client into `frontend/src/ChatPanel.tsx`. It validates and renders the actual POST `/api/chat` response directly. It no longer waits for an extra message-history GET that could replace the answer with an older snapshot. History requests are aborted and generation-checked on navigation.
- Reproduced and fixed a fast-follow-up race: the URL acknowledgement for a newly created conversation could invalidate the next reply, and the next request could capture a still-null URL conversation ID. The client now retains the committed conversation ID and distinguishes acknowledgement from external navigation.
- Scroll to the newest answer, validate response/history shapes, and show real API/protocol errors rather than synthesizing a generic insufficient-evidence fallback.
- Pass the resolved follow-up query, including the confirmed context medicine, to passage selection. The active provider remains the configured extractive provider; optional external/local providers were not falsely presented as running.
- Keep medical grounding and emergency/dose-change safeguards. The new nonmedical clarification path is validated by recomputing the expected source-derived candidates and exact clarification response. Arbitrary medical prose cannot use that path to bypass validation.
- Anchor SQLite and `.env` resolution to the repository root, preventing a service started from another directory from silently opening a different relative database. No existing accounts, conversations, or medical source records were rewritten.
- Expose operational runtime/build IDs and a corpus fingerprint for verification. Chat diagnostics record retrieved passage count, resolved query, and citation-validation outcome; no private chain-of-thought is exposed.

## Actual browser/API/database verification

Both services were restarted. The browser called the real Vite `/api/chat` proxy and FastAPI endpoint; no route mocking or response substitution was used. Playwright compared each rendered assistant message ID and each citation URL/count against the real POST JSON. It also asserted that the latest answer was visible.

The browser corpus fingerprint matched a direct SQLAlchemy read of the application database: `1bc15f8ae790fa78` with **3 available documents / 27 chunks**. The captured runtime was `1dcee7f49870`, build `9918f91b2cc7`. These are observations from the run, not hardcoded success criteria; each test reads and compares the current values dynamically.

The raw artifact `runtime/chat-runtime-results.json` contains **15 real chat request/response captures**, including full returned answers, citation IDs/URLs, diagnostic metadata, and rendered message IDs. `runtime/chat-live-answer.png` is the actual browser screenshot. Test accounts were generated under `@example.test` and removed by exact-account teardown.

| Browser action | Observed outcome | Citations |
|---|---|---:|
| Source-derived starter button | Evidence-backed response | 2 |
| Common side effects of Paracetamol | `LIMITED_EVIDENCE`, validation passed | 2 |
| What is ibuprofen used for? | `LIMITED_EVIDENCE`, validation passed | 1 |
| How should paracetamol be stored? | `LIMITED_EVIDENCE`, validation passed | 1 |
| Each of the three actual spelling variants | Explicit medicine-name confirmation, no assumed equivalence | 0 before confirmation |
| Confirm Paracetamol after each spelling variant | `LIMITED_EVIDENCE`, validation passed | 2 each |
| Generated follow-up button | Evidence-backed response | 2 |
| Generic medication-storage question | Medicine/topic choice, followed by sourced storage answer | 1 after choice |
| FictionalDrugQ | `INSUFFICIENT_EVIDENCE`, validation passed | 0 |

Final checks: **55 backend tests**, **15 frontend tests**, and **3 real-browser workflows** passed. TypeScript/Vite production build passed. The 15-case real-corpus diagnostic suite and Alembic drift check passed. The live HTTP proxy smoke test, including grounded chat and unknown-medicine abstention, passed; frontend and backend health checks returned 200. Browser page errors: **0**.

## Reproduce

With both services running and the official references imported:

```powershell
.\.venv\Scripts\python.exe -m pytest -c backend/pytest.ini -q backend/tests
.\.venv\Scripts\python.exe scripts/smoke_test.py
.\.venv\Scripts\python.exe scripts/diagnose_rag.py
Set-Location frontend
node ..\.tools\package\bin\npm-cli.js test
node ..\.tools\package\bin\npm-cli.js run build
node ..\.tools\package\bin\npm-cli.js run test:e2e
```

Use `npm` instead of the workspace-local npm fallback where available. In the application, refresh, choose **New conversation**, and use a displayed source-backed question or type an exact medicine name. For a near spelling, check the packet and click the confirmation button before receiving medical information. Previously saved abstentions remain historical records; they are not silently regenerated.

These tests verify software integration and source traceability, not clinical validation or coverage of every medicine. No medical safety check was disabled, and no medical answer or citation was hardcoded.
