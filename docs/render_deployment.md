# Render backend deployment, preserving the frontend

The selected repository is `https://github.com/lachaiahgarivaishnavi18-droid/MediGuide-AI`. It initially contained only a README. This project includes a Docker-based backend and a `render.yaml` Blueprint for one API service plus one PostgreSQL database. The Blueprint does not define or deploy a frontend.

## 1. Connect your account and repository

Sign in at https://dashboard.render.com/ using your own account. Choose **New + → Blueprint**, connect GitHub, and authorize access to the selected repository. Select the branch containing the backend deployment files and its `render.yaml`. Review the service and database before creating them. Do not enter credentials into chat.

The prepared Blueprint uses free plans and the Singapore region. Render's free PostgreSQL database expires after 30 days; this is a temporary demonstration configuration. Free web services sleep after inactivity and have ephemeral local files. Choose a suitable persistent database plan in your own account for longer use; no paid resources have been provisioned by this preparation.

## 2. Set environment variables

| Variable | Value |
|---|---|
| `DATABASE_URL` | Automatically connected to Render PostgreSQL by the Blueprint. Do not use SQLite or paste the connection string into chat. |
| `ENVIRONMENT` | `production` |
| `COOKIE_SECURE` | `true` |
| `CORS_ORIGINS` | Initially empty while the frontend URL is unavailable. This allows no browser origin. Later set the exact `https://YOUR-FRONTEND.vercel.app` origin, without a trailing slash. Multiple trusted origins can be comma separated. |
| `ADMIN_EMAIL` | Your administrator email, entered in Render's environment form. |
| `ADMIN_PASSWORD` | A unique password of at least 12 characters, entered only in Render. |
| `LLM_PROVIDER` | `extractive` (does not need an external LLM key) |
| `EMBEDDING_PROVIDER` | `fastembed` |
| `EMBEDDING_MODEL` | `sentence-transformers/all-MiniLM-L6-v2` |
| `EMBEDDING_LOCAL_FILES_ONLY` | `true` |
| `IMPORT_TRUSTED_REFERENCES_ON_START` | `true` |

Render supplies `PORT`; the startup script binds to `0.0.0.0:$PORT`. The database URI is normalized to use the installed Psycopg 3 driver. Models are downloaded while building the Docker image, so no medical questions are sent to an embedding provider. Startup runs migrations, seeds roles/admin when configured, and imports the approved source catalog when required. PostgreSQL stores accounts, conversations, documents and chunks; the local FAISS index is a rebuildable cache. WHO local-only educational extracts are excluded from production imports.

First source import can take several minutes. A source verification failure stops startup instead of silently launching an empty or fabricated knowledge base. Inspect Render's logs if the service does not become healthy.

## 3. Verify Render before connecting Vercel

Once Render reports **Live**, copy its actual HTTPS service URL. Do not infer the URL from the service name. Open:

- `https://YOUR-ACTUAL-SERVICE.onrender.com/health`: should return `{"status":"ok"}` and verifies database connectivity.
- `https://YOUR-ACTUAL-SERVICE.onrender.com/api/system/status`: should return MediGuide runtime and build identifiers.
- After sign-in, `/api/knowledge/status`: should show the production source corpus and FastEmbed provider.

Test the real chat API using an isolated test account before exposing it through the frontend. Check the seven medical regression questions, citation URLs, a pasted refusal, an unknown medicine, and emergency escalation. Do not count a successful build as successful chatbot verification.

## 4. Connect the existing frontend without redeployment

The current frontend uses relative `/api` requests. Vercel supports **project-level routing rules**, which can proxy these requests to Render without a frontend code change or redeployment.

In the existing Vercel project, open its routing-rule settings or the official API external-origin routing-rule template. Add a rewrite for `/api/:path*` to `https://YOUR-ACTUAL-SERVICE.onrender.com/api/:path*`. Preserve the `/api` prefix in the destination. Review the staged rule and publish only that rule. Do not add a catch-all rule or change the frontend deployment. Add a separate `/health` rewrite only if needed for same-origin diagnostics.

Set Render's `CORS_ORIGINS` to the exact existing frontend origin. This may restart only the backend. Keep authentication cookies on the same frontend origin by using the proxy; do not switch the browser to direct cross-site cookie calls.

Visit the existing frontend URL and verify sign-in, medical answers, source links, insufficient-evidence behavior and emergency routing. Record the existing Vercel deployment identity before and after routing configuration; its frontend deployment should remain unchanged. If another `/api` project rule already exists, inspect it before replacing anything.

Official references: https://render.com/docs/blueprint-spec, https://render.com/docs/free, https://render.com/docs/configure-environment-variables, https://vercel.com/templates/other/add-api-external-origin-routing-rule.

## Current status

The tested backend-only source is published on branch `codex/render-backend`; the `main` branch remains unchanged. Backend verification: 69 tests passed. A live Render URL and a Vercel frontend URL are not yet available. Actual cloud deployment and end-to-end verification require creating the Blueprint in your authenticated Render account. No frontend deployment was triggered. The backend branch disables its own Vercel automatic deployment through `vercel.json`. Docker/cloud execution has not yet been verified in this environment.
