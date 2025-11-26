# app/domain/services/company_service.py
from __future__ import annotations

from typing import Optional, Sequence
from uuid import UUID

from app.domain.models.company import Company
from app.domain.repositories.company_repository import CompanyRepository
from app.domain.events.event_bus import event_bus
from app.domain.events.company_events import CompanyUpdatedEvent


class CompanyService:
    """
    Application-Service rund um Companies (Accounts/Sub-Companies).

    Verantwortlichkeiten:
      - Kapselt CompanyRepository
      - Setzt Audit-Felder
      - Publiziert Domain-Events
    """

    def __init__(self, companies: CompanyRepository) -> None:
        self._companies = companies

    # ------------------------------------------------------------------ #
    # Reads
    # ------------------------------------------------------------------ #

    async def get_company(
        self,
        tenant_id: UUID,
        leadlane_sub_company_id: UUID,
    ) -> Optional[Company]:
        return await self._companies.get(tenant_id, leadlane_sub_company_id)

    async def list_companies_for_tenant(
        self,
        tenant_id: UUID,
        limit: int = 100,
        offset: int = 0,
    ) -> Sequence[Company]:
        return await self._companies.list_for_tenant(tenant_id, limit=limit, offset=offset)

    # ------------------------------------------------------------------ #
    # Writes
    # ------------------------------------------------------------------ #

    async def save_company(
        self,
        company: Company,
        actor: Optional[str] = None,
    ) -> Company:
        """
        Zentrale Write-Methode für Companies.

        - tenant_id muss gesetzt sein
        - Audit-Felder (created_by/modified_by) werden gepflegt
        - CompanyUpdatedEvent wird publiziert
        """
        if company.tenant_id is None:
            raise ValueError(
                "company.tenant_id darf nicht None sein, bevor sie gespeichert wird."
            )

        # Audit
        if company.created_by is None:
            company.created_by = actor or "system_sync"
        company.modified_by = actor or "system_sync"

        # 1) Speichern
        saved = await self._companies.save(company)

        # 2) Domain-Event feuern (asynchron im Hintergrund)
        event = CompanyUpdatedEvent(
            tenant_id=saved.tenant_id,  # type: ignore[arg-type]
            leadlane_sub_company_id=saved.leadlane_sub_company_id,  # type: ignore[arg-type]
            metadata={"source": "company_service.save_company"},
        )
        event_bus.publish_background(event)

        return saved
