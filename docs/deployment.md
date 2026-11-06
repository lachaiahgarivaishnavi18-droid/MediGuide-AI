# Deployment

Local execution supports Python 3.12, SQLite, and Vite. Docker Compose defines PostgreSQL, FastAPI, and Nginx/React. This repository's full Python backend is not compatible with static-only hosting or a Cloudflare Worker runtime. No cloud deployment is performed by creating these files.

1. Configure `.env` with a random URL-safe PostgreSQL password, explicit administrator credentials, exact frontend origin, and any model credentials. Never commit `.env`.
2. Build with `docker compose build`, then start with `docker compose up -d`. Inspect `docker compose ps` and `docker compose logs backend`.
3. Verify `/health` and sign in from the frontend. Confirm migration completion and private source upload/approval on a disposable test document before importing permitted real reference material.
4. Put the frontend behind HTTPS; configure its public origin and `COOKIE_SECURE=true`. Keep database/backend internal. Set proxy upload and timeout limits. Restrict backend OpenAPI documentation at the perimeter if appropriate.
5. Back up PostgreSQL with verified restoration procedures. Apply migrations as an explicit release operation when scaling beyond a single service startup. Do not run concurrent migrations from multiple replicas.
6. Replace process-local throttling and per-query vector rebuilding before multi-worker/high-volume deployments. Add central health monitoring without logging raw questions, source uploads, or model secrets.
7. Establish source licensing review, qualified clinical curation, refresh/withdrawal policies, incident response, privacy retention, identity recovery, security testing, accessibility review, and expert evaluation. Do not present this development build as clinically certified.

Sentence Transformers is optional and is not included in the default container image. For semantic mode, extend the image with `requirements-ml.txt`, preload the selected model under an approved cache policy, and validate retrieval performance. API/local LLM selection requires a compatible chat-completions endpoint; API mode requires a key/model. An unavailable provider returns a transparent error; it never swaps in fabricated answers.

Runtime files, `.env`, dependencies, databases, and generated build directories are ignored by Git/Docker context where appropriate. Production images should be rebuilt and scanned regularly, pinned to organization-approved digests, and monitored for dependency advisories. See `docs/verification.md` for checks actually completed in this workspace.
