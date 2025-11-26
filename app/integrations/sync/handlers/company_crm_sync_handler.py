# app/integrations/sync/handlers/company_crm_sync_handler.py
from __future__ import annotations

import logging
from typing import Callable, Awaitable

from app.domain.events.company_events import CompanyUpdatedEvent
from app.domain.repositories.company_repository import CompanyRepository
from app.integrations.crm.crm_types import CRMCompanyPayload
from app.integrations.sync.crm_sync_listener import CRMSyncListener

logger = logging.getLogger(__name__)


def make_company_updated_handler(
    crm_sync_listener: CRMSyncListener,
    company_repository: CompanyRepository,
) -> Callable[[CompanyUpdatedEvent], Awaitable[None]]:
    """
    Factory, die einen Event-Handler für CompanyUpdatedEvent baut.
    Der Handler:
      - lädt die Company aus dem Repository
      - mappt auf CRMCompanyPayload
      - ruft CRMSyncListener.on_company_changed auf
    """

    async def handle(event: CompanyUpdatedEvent) -> None:
        if event.tenant_id is None:
            logger.warning(
                "CompanyUpdatedEvent ohne tenant_id empfangen – skip. event_id=%s",
                event.id,
            )
            return

        company = await company_repository.get(
            tenant_id=event.tenant_id,
            leadlane_sub_company_id=event.leadlane_sub_company_id,
        )
        if company is None:
            logger.warning(
                "Company für Event nicht gefunden – skip. tenant_id=%s, sub_company_id=%s",
                event.tenant_id,
                event.leadlane_sub_company_id,
            )
            return

        # Minimales Mapping Company -> CRMCompanyPayload.
        # Wir nutzen getattr, damit es nicht crasht, wenn einzelne Felder im Domain-Modell fehlen.
        payload = CRMCompanyPayload(
            leadlane_sub_company_id=str(event.leadlane_sub_company_id),
            central_sub_company_id=getattr(company, "central_sub_company_id", None),
            central_parent_company_id=getattr(company, "central_parent_company_id", None),
            tenant_parent_company_id=getattr(company, "tenant_parent_company_id", None),
            name=getattr(company, "name", "Unknown Company"),
            business_description=getattr(company, "business_description", None),
            country_region=getattr(company, "country_region", None),
            city=getattr(company, "city", None),
            postal_code=getattr(company, "postal_code", None),
            address_line_1=getattr(company, "address_line_1", None),
            url=getattr(company, "url", None),
            website=getattr(company, "website", None),
            linkedin_account=getattr(company, "linkedin_account", None),
            email_address=getattr(company, "email_address", None),
            phone=getattr(company, "phone", None),
            phone_alt=getattr(company, "phone_alt", None),
            employees_total=getattr(company, "employees_total", None),
            sales_eur=getattr(company, "sales_eur", None),
            year_founded=getattr(company, "year_founded", None),
            primary_industry_code=getattr(company, "primary_industry_code", None),
            primary_industry_system=getattr(company, "primary_industry_system", None),
            duns_number=getattr(company, "duns_number", None),
            lifecycle_phase=getattr(company, "lifecycle_phase", None),
            loss_reason=getattr(company, "loss_reason", None),
            responsible_sdr_id=getattr(company, "responsible_sdr_id", None),
            account_summary_gpt=getattr(company, "account_summary_gpt", None),
            company_description_leadlane=getattr(
                company, "company_description_leadlane", None
            ),
            properties={},  # falls du später Custom-Properties aus der DB laden willst
        )

        logger.info(
            "Handling CompanyUpdatedEvent -> CRM Sync: tenant_id=%s, sub_company_id=%s",
            event.tenant_id,
            event.leadlane_sub_company_id,
        )

        await crm_sync_listener.on_company_changed(
            tenant_id=event.tenant_id,
            payload=payload,
        )

    return handle
