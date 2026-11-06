import logging
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.api.routes import router

logging.basicConfig(level=logging.INFO)
app = FastAPI(title="MediGuide AI", version="0.1.0", description="Evidence-linked patient education. Not a clinical decision system.")
app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origins.split(","), allow_credentials=True, allow_methods=["GET", "POST", "PATCH", "DELETE"], allow_headers=["Content-Type"])


@app.middleware("http")
async def headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Cache-Control"] = "no-store"
    return response


app.include_router(router)


@app.get("/api/openapi.json", include_in_schema=False)
def proxied_schema():
    return app.openapi()


@app.get("/health")
def health():
    from sqlalchemy import text
    from app.database.session import engine
    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))
    return {"status": "ok"}
