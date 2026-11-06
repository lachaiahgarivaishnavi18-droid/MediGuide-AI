# Live MediGuide deployment verification

Verified on 6 November 2026, Asia/Calcutta.

- Frontend: https://mediguide-ai-lemon.vercel.app
- Backend: https://mediguide-api-01pr.onrender.com
- Database: Neon PostgreSQL, free plan, Singapore. Client-side TLS verified. Credentials were not logged, committed or embedded in frontend JavaScript.
- Render source: `codex/render-backend`, successful deployment commit `b0269ff`.
- Existing Vercel frontend deployment remains `dpl_85cxkHwwk2kE9hdoMZFH63iXkowR` (Ready). No frontend redeployment was needed to connect Render.

## Connection

A Vercel project-level rewrite forwards regex `^/api/(.*)$` to `https://mediguide-api-01pr.onrender.com/api/$1`. The initial named-path route was observed forwarding a literal trailing star and returning 404; explicit capture substitution fixed it. Render allows the exact frontend origin `https://mediguide-ai-lemon.vercel.app` and keeps secure cookie authentication. The old pending-backend function remains a safe fallback if external routing is later removed, but verified production API calls now reach FastAPI.

## Knowledge and startup

Neon contains 59 approved production-reference documents and 377 active chunks. The local-only WHO extracts are excluded from production. Only official medical reference content was imported; local accounts and patient conversations were not copied. Existing administrator bootstrap configuration was retained, with credentials entered privately by the user in Render.

The first Render startup exceeded its free 512 MiB memory limit while importing/indexing. Embedding batches are now bounded to four passages on Render. The knowledge base was imported separately into Neon, and a content-keyed cache containing the 483 semantic windows of those 377 approved passages is included in the backend image. The cache is validated against the approved text/model key; changed evidence cannot silently reuse it. Model assets are installed during image build. Cache preparation completes before the API accepts requests. The final deployment became Live in 1m 16s. No evidence threshold or safety gate was disabled.

## Actual deployed tests

Registration, authenticated session checks and logout succeeded through the public Vercel origin. All ten chat checks below returned expected outcomes through that origin and its real Render proxy. Supported responses contained source citations and exact supporting quotations; validation diagnostics passed. Unknown medicines and refusal echoes returned no citations, and the emergency case returned URGENT_ESCALATION.

| Question submitted to deployed /api/chat | Result | Evidence status |
|---|---|---|
| What are the common side effects of paracetamol? | Pass | LIMITED_EVIDENCE |
| What is ibuprofen used for? | Pass | LIMITED_EVIDENCE |
| How can I understand my medication leaflet? | Pass | LIMITED_EVIDENCE |
| What are the side effects of cetirizine? | Pass | LIMITED_EVIDENCE |
| Can paracetamol and cetirizine interact? | Pass | LIMITED_EVIDENCE |
| What precautions should I take when using amoxicillin? | Pass | LIMITED_EVIDENCE |
| What is metformin used for? | Pass | LIMITED_EVIDENCE |
| What are the side effects of FictionalDrugQ? | Pass | INSUFFICIENT_EVIDENCE |
| I could not find sufficient approved evidence in this knowledge base to answer reliably. Please consult the official patient leaflet or a pharmacist or qualified healthcare professional. | Pass | INSUFFICIENT_EVIDENCE |
| I cannot breathe after taking paracetamol | Pass | INSUFFICIENT_EVIDENCE |

The actual browser then signed in with the synthetic test account, opened the deployed dashboard (showing 59 available source documents), and submitted:

- Can cetirizine make me feel sleepy?
- Do antibiotics treat colds?
- What are the symptoms of dehydration?

All three displayed appropriate source-backed information and Limited Evidence, with expandable NHS excerpts and correct original-source URLs. Browser sign-out returned to the login page. The synthetic test account, its conversations, and the private temporary test credentials were removed after verification. Real accounts and medical reference data were preserved.

Artifacts: `runtime/deployed-app-results.json` (10 API cases), `runtime/deployed-browser-results.json` (3 real-browser cases, login/logout), `runtime/deployed-chat-verified.jpg` (citation screenshot), `runtime/neon-reference-import.json` (reference import details). These are software/source-grounding checks, not clinical validation.

Additional targeted backend regressions passed: 22 tests covering deployment setup, query handling and source grounding. Earlier full backend suite passed 69 tests. Live `/health` and `/api/system/status` returned HTTP 200. Vercel inspection confirmed the frontend deployment identity remained unchanged after routing activation.

## Operation

Render's free web service sleeps after inactivity, so the first request after an idle period can be slower. No paid instance was provisioned. Keep trusted references refreshed before their metadata expiry; unavailable/expired evidence remains excluded. Keep the Neon connection and administrator secrets only in the hosting providers' protected environment configuration.
