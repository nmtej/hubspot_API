# app/main.py (nur relevante Teile)

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
import logging
from contextlib import asynccontextmanager
from typing import AsyncIterator

from app.config import settings
from app.db.database import Database

from app.domain.events.event_bus import event_bus
from app.domain.events.company_events import CompanyUpdatedEvent
from app.domain.repositories.company_repository import CompanyRepository

from app.integrations.mapping import (
    CRMFieldMappingsRepository,
    CRMFieldMappingEngine,
    CRMAccountLinksRepository,
    CRMContactLinksRepository,
    CRMOpportunityLinksRepository,
)
from app.integrations.credentials.crm_credentials_store import CRMCredentialsStore
from app.integrations.sync.crm_sync_service import CRMSyncService
from app.integrations.sync.crm_sync_listener import CRMSyncListener
from app.integrations.sync.handlers.company_crm_sync_handler import (
    make_company_updated_handler,
)

from app.api.admin_crm_router import admin_crm_router
from app.api.tenant_crm_router import tenant_crm_router
from app.api.crm_field_mapping_router import crm_field_mapping_router
from app.api.crm_webhook_router import crm_webhook_router
from app.api.error_handlers import (
    http_exception_handler,
    unhandled_exception_handler,
    validation_exception_handler,
)


logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # We are NOT using the local Postgres database.
    # Do NOT connect/disconnect at startup to avoid asyncpg errors.
    yield

def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        debug=settings.debug,
        lifespan=lifespan,
    )

    # Error-Handler
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)

    # CORS
    if settings.cors_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=[str(o) for o in settings.cors_origins],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    # -----------------------------------------------
    # Router / Endpunkte
    # -----------------------------------------------

    # Admin Router (FDE kann Credentials setzen)
    app.include_router(
        admin_crm_router,
        prefix=settings.api_prefix,
    )

    # Tenant-CRM-Router (HubSpot Connect etc.)
    app.include_router(
        tenant_crm_router,
        prefix=settings.api_prefix,
    )

    # CRM Field-Mappings
    app.include_router(
        crm_field_mapping_router,
        prefix=settings.api_prefix,
    )

    # CRM Webhooks (z.B. HubSpot)
    app.include_router(
        crm_webhook_router,
        prefix=settings.api_prefix,
    )

    @app.get("/health", tags=["system"])
    async def health() -> dict:
        return {
            "status": "ok",
            "app": settings.app_name,
            "version": settings.app_version,
            "environment": settings.environment,
        }

    @app.get("/", include_in_schema=False)
    async def root() -> dict:
        return {
            "message": "LeadLane API",
            "docs_url": "/docs",
            "redoc_url": "/redoc",
        }

    return app


app = create_app()


