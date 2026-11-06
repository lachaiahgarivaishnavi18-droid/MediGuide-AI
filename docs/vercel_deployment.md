# Vercel deployment

Deploy the React/Vite frontend from `frontend/`. The existing FastAPI backend needs a hosted HTTPS service and persistent PostgreSQL storage. Its current local SQLite database, model cache and FAISS files must not be treated as durable Vercel Function storage. Local user conversations and credentials are not included in the frontend upload.

## Prepared configuration

After the backend is hosted, run from the repository root:

```powershell
node scripts/prepare_vercel.mjs --backend-url https://YOUR-HOSTED-BACKEND
```

This checks `/health` and the MediGuide runtime identity, then writes `frontend/vercel.json`. API requests and health checks are forwarded to that backend before the SPA route fallback. Browser requests remain on the Vercel origin, preserving the existing cookie-based authentication flow. The script does not accept localhost, credentials in URLs, or a backend URL containing an `/api` path prefix.

Configure the hosted backend with `ENVIRONMENT=production`, its persistent `DATABASE_URL`, `COOKIE_SECURE=true`, and `CORS_ORIGINS` containing the exact Vercel frontend origin. Install model assets and run migrations/source import on that backend using the existing deployment guide. Import trusted medical sources; do not copy the local database containing user accounts and conversations to a public deployment. WHO local educational extracts remain excluded in production mode.

After authenticating the Vercel CLI, deploy from `frontend/`:

```powershell
vercel --prod
```

Use Vite, build command `npm run build`, output directory `dist`. Do not deploy before generating and reviewing the verified backend routing configuration. The development Vite proxy is not included in a Vercel production build.

After deployment, verify public `/health`, sign-in/session cookies, source-backed chat answers, source links, emergency handling, and unsupported-evidence abstention. Run the existing browser suite against the deployed URL with `E2E_URL` set to it. A frontend URL alone does not verify a working medical chatbot.

## Current access needed

No Vercel account credentials or project connection were configured when deployment preparation began. A public backend origin was also unavailable. No production URL is claimed until Vercel returns a successful deployment and the deployed chat flow is verified.
