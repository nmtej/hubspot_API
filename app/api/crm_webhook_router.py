# app/api/crm_webhook_router.py
from __future__ import annotations

from typing import Any, Dict, List, Mapping
from uuid import UUID

from fastapi import APIRouter, Request, Depends, HTTPException, status

from app.integrations.mapping import CRMFieldMappingEngine, CRMAccountLinksRepository
from app.integrations.crm.crm_types import CRMSystem
from app.domain.repositories.company_repository import CompanyRepository
from app.integrations.webhooks.webhook_idempotency_repository import (
    WebhookIdempotencyRepository,
)
from app.integrations.webhooks.webhook_security import verify_webhook_signature
from app.integrations.webhooks.hubspot_company_webhook_processor import (
    HubSpotCompanyWebhookProcessor,
)
from app.dependencies import (
    get_db,
    get_crm_field_mapping_engine,
    get_account_links_repo,
)
from app.db.database import Database

crm_webhook_router = APIRouter(
    prefix="/crm/webhooks",
    tags=["crm-webhooks"],
)


def get_tenant_id_from_headers(request: Request) -> UUID:
    """
    Derzeit: Tenant-ID aus Header X-Tenant-Id lesen.
    (Webhook kommt von HubSpot, kein JWT – das kann man später härten.)
    """
    raw = request.headers.get("X-Tenant-Id")
    if not raw:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing X-Tenant-Id header",
        )
    try:
        return UUID(raw)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid X-Tenant-Id header",
        )


def get_hubspot_company_processor(
    tenant_id: UUID = Depends(get_tenant_id_from_headers),
    db: Database = Depends(get_db),
    mapping_engine: CRMFieldMappingEngine = Depends(get_crm_field_mapping_engine),
    account_links_repo: CRMAccountLinksRepository = Depends(get_account_links_repo),
) -> HubSpotCompanyWebhookProcessor:
    idempotency_repo = WebhookIdempotencyRepository(db)
    company_repo = CompanyRepository(db)

    return HubSpotCompanyWebhookProcessor(
        tenant_id=tenant_id,
        company_repo=company_repo,
        account_links_repo=account_links_repo,
        mapping_engine=mapping_engine,
        idempotency_repo=idempotency_repo,
    )


@crm_webhook_router.post("/{crm_system}", summary="Webhook-Empfänger für CRM-Systeme")
async def handle_crm_webhook(
    crm_system: CRMSystem,
    request: Request,
    hubspot_company_processor: HubSpotCompanyWebhookProcessor = Depends(
        get_hubspot_company_processor
    ),
):
    # 1. Body + Headers lesen
    raw_body = await request.body()
    headers: Mapping[str, str] = dict(request.headers)

    # 2. Signatur prüfen (für HubSpot, andere CRMs später)
    request_uri = request.url.path
    if request.url.query:
        request_uri = f"{request_uri}?{request.url.query}"

    verify_webhook_signature(
        crm_system=crm_system,
        headers=headers,
        raw_body=raw_body,
        method=request.method,
        request_uri=request_uri,
    )

    # 3. JSON-Payload lesen
    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid JSON payload",
        )

    # 4. CRM-spezifisch verzweigen
    if crm_system == CRMSystem.HUBSPOT:
        # HubSpot schickt typischerweise ein Array von Events
        if isinstance(payload, list):
            events: List[Dict[str, Any]] = payload
        else:
            events = payload.get("events") or []
            if not isinstance(events, list):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Expected a list of events for HubSpot webhook payload",
                )

        await hubspot_company_processor.handle_events(events)

        return {"status": "ok", "processed_events": len(events)}

    # Andere CRMs noch nicht implementiert
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail=f"Webhook handling for CRM system '{crm_system.value}' not implemented yet.",
    )
