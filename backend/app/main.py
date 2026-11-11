import logging
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.exc import InterfaceError, OperationalError, TimeoutError as PoolTimeoutError
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


@app.exception_handler(InterfaceError)
@app.exception_handler(OperationalError)
@app.exception_handler(PoolTimeoutError)
async def database_unavailable(request: Request, error: Exception):
    logging.getLogger(__name__).warning('Database temporarily unavailable (%s)', type(error).__name__)
    return JSONResponse(
        status_code=503,
        content={'code': 'DATABASE_UNAVAILABLE', 'detail': 'The account database is temporarily unavailable.'},
    )


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
