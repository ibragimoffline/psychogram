from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from src.api.routers.auth import router as auth_router
from src.api.routers.read import router as read_router
from src.api.routers.v1 import router as v1_router
from src.core.config import Settings, get_settings
from src.core.db import Database
from src.core.errors import DomainError, domain_error_handler
from src.core.middleware import APISecurityMiddleware
from src.models.domain import Base


def create_app(
    settings: Settings | None = None, database: Database | None = None
) -> FastAPI:
    runtime_settings = settings or get_settings()
    runtime_database = database or Database(runtime_settings)

    @asynccontextmanager
    async def lifespan(_app: FastAPI):
        if runtime_settings.auto_create_schema:
            Base.metadata.create_all(runtime_database.engine)
        yield

    application = FastAPI(
        title=runtime_settings.app_name,
        version=runtime_settings.app_version,
        description=(
            "Multi-tenant psychological research scoring API. "
            "It does not provide medical diagnoses."
        ),
        lifespan=lifespan,
    )
    application.state.settings = runtime_settings
    application.state.database = runtime_database
    application.add_exception_handler(DomainError, domain_error_handler)
    application.add_middleware(
        CORSMiddleware,
        allow_origins=runtime_settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=[
            "Authorization",
            "Content-Type",
            "X-Organization-ID",
            "Idempotency-Key",
        ],
        expose_headers=[
            "Content-Disposition",
            "X-Export-Rows",
            "X-Export-Not-Calculated",
            "X-Export-Excluded-Consent",
        ],
    )
    application.add_middleware(
        APISecurityMiddleware,
        max_request_body_bytes=runtime_settings.max_request_body_bytes,
    )
    application.include_router(auth_router)
    application.include_router(v1_router)
    application.include_router(read_router)

    @application.get("/", tags=["system"])
    def root():
        return {
            "name": runtime_settings.app_name,
            "version": runtime_settings.app_version,
        }

    @application.get("/health", tags=["system"])
    def health():
        with runtime_database.session_factory() as db:
            db.execute(text("SELECT 1"))
        return {"status": "healthy", "database": "reachable"}

    return application


app = create_app()
