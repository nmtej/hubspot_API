# app/integrations/webhooks/hubspot_company_webhook_processor.py
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Iterable, Mapping
from uuid import UUID

from fastapi import HTTPException, status

from app.domain.models.company import Company
from app.domain.repositories.company_repository import CompanyRepository
from app.integrations.crm.crm_types import CRMSystem
from app.integrations.mapping import CRMAccountLinksRepository, CRMFieldMappingEngine
from app.integrations.webhooks.webhook_idempotency_repository import (
    WebhookIdempotencyRepository,
)


class HubSpotCompanyWebhookProcessor:
    """
    Verarbeitet HubSpot-Webhook-Events für Companies.
    """

    def __init__(
        self,
        *,
        tenant_id: UUID,
        company_repo: CompanyRepository,
        account_links_repo: CRMAccountLinksRepository,
        mapping_engine: CRMFieldMappingEngine,
        idempotency_repo: WebhookIdempotencyRepository,
    ) -> None:
        self.tenant_id = tenant_id
        self.company_repo = company_repo
        self.account_links_repo = account_links_repo
        self.mapping_engine = mapping_engine
        self.idempotency_repo = idempotency_repo

    async def handle_events(
        self,
        events: Iterable[Mapping[str, Any]],
    ) -> None:
        """
        Erwartet eine Liste von HubSpot-Events.

        Vereinfachte Annahme für HubSpot v3:
        - ev["eventId"] / "event_id": eindeutige Event-ID
        - ev["occurredAt"] (ms since epoch) oder "occurred_at": Timestamp
        - ev["objectId"] / "object_id"]: HubSpot Company ID
        - ev["properties"]: Dict[str, Any] der Felder
        (Passe das bei Bedarf an eure echte HubSpot-Payload an.)
        """

        for ev in events:
            event_id = str(
                ev.get("eventId")
                or ev.get("event_id")
                or ev.get("id")
                or ""
            ).strip()
            if not event_id:
                # Ohne Event-ID können wir keine Idempotenz machen → lieber 400
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Missing event_id in HubSpot webhook payload",
                )

            occurred_raw = ev.get("occurredAt") or ev.get("occurred_at")
            if occurred_raw:
                # HubSpot schickt i.d.R. ms since epoch
                if isinstance(occurred_raw, (int, float)):
                    occurred_at = datetime.utcfromtimestamp(occurred_raw / 1000.0)
                else:
                    # Fallback: ISO8601-String etc. – bei Bedarf anpassen
                    occurred_at = datetime.fromisoformat(str(occurred_raw))
            else:
                occurred_at = None

            # Idempotenz: ist das Event neu?
            is_new = await self.idempotency_repo.try_mark_received(
                crm_system=CRMSystem.HUBSPOT.value,
                event_id=event_id,
                occurred_at=occurred_at,
            )
            if not is_new:
                # Duplikat → einfach überspringen
                continue

            hubspot_company_id = str(
                ev.get("objectId")
                or ev.get("object_id")
                or ev.get("companyId")
                or ""
            ).strip()
            if not hubspot_company_id:
                await self.idempotency_repo.mark_processed(
                    crm_system=CRMSystem.HUBSPOT.value,
                    event_id=event_id,
                    status="skipped_no_object_id",
                )
                continue

            # Link HubSpot Company ID → LeadLane SubCompany ID
            link = await self.account_links_repo.get_by_crm_id(
                tenant_id=self.tenant_id,
                crm_system=CRMSystem.HUBSPOT,
                crm_account_id=hubspot_company_id,
            )
            if not link:
                # Company ist uns (noch) nicht bekannt → optional später "on the fly" anlegen
                await self.idempotency_repo.mark_processed(
                    crm_system=CRMSystem.HUBSPOT.value,
                    event_id=event_id,
                    status="skipped_no_link",
                )
                continue

            # Company aus der DB laden
            company = await self.company_repo.get_by_id(
                tenant_id=self.tenant_id,
                leadlane_sub_company_id=UUID(link.leadlane_sub_company_id),
            )
            if not company:
                await self.idempotency_repo.mark_processed(
                    crm_system=CRMSystem.HUBSPOT.value,
                    event_id=event_id,
                    status="skipped_no_company",
                )
                continue

            # Out-of-order: Ist das Event älter als der bekannte Stand?
            if occurred_at and occurred_at <= company.last_modified_time:
                await self.idempotency_repo.mark_processed(
                    crm_system=CRMSystem.HUBSPOT.value,
                    event_id=event_id,
                    status="skipped_out_of_order",
                )
                continue

            properties: Dict[str, Any] = ev.get("properties") or {}

            # CRM → UDM mappen (Patch)
            updated_company: Company = await self.mapping_engine.map_crm_to_udm(
                tenant_id=self.tenant_id,
                crm_system=CRMSystem.HUBSPOT,
                object_type="company",
                crm_properties=properties,
                udm_cls=Company,
                existing=company,
            )

            # In DB speichern
            await self.company_repo.save(updated_company)

            # Status auf processed setzen
            await self.idempotency_repo.mark_processed(
                crm_system=CRMSystem.HUBSPOT.value,
                event_id=event_id,
                status="processed",
            )
