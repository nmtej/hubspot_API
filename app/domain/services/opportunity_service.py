# app/domain/services/opportunity_service.py
from __future__ import annotations

from typing import Optional, Sequence
from uuid import UUID

from app.domain.models.opportunity import Opportunity
from app.domain.repositories.opportunity_repository import OpportunityRepository


class OpportunityService:
    """
    Application-Service rund um Opportunities (Demos).

    Verantwortlichkeiten:
      - Kapselt OpportunityRepository
      - Setzt Audit-Felder
      - Bietet einfache Query-Methoden
    """

    def __init__(self, opportunities: OpportunityRepository) -> None:
        self._opportunities = opportunities

    # ------------------------------------------------------------------ #
    # Reads
    # ------------------------------------------------------------------ #

    async def get_opportunity(
        self,
        tenant_id: UUID,
        leadlane_demo_id: UUID,
    ) -> Optional[Opportunity]:
        return await self._opportunities.get(tenant_id, leadlane_demo_id)

    async def list_opportunities_for_tenant(
        self,
        tenant_id: UUID,
        limit: int = 100,
        offset: int = 0,
    ) -> Sequence[Opportunity]:
        return await self._opportunities.list_for_tenant(
            tenant_id, limit=limit, offset=offset
        )

    async def list_opportunities_for_company(
        self,
        tenant_id: UUID,
        leadlane_account_id: UUID,
        limit: int = 100,
        offset: int = 0,
    ) -> Sequence[Opportunity]:
        return await self._opportunities.list_for_company(
            tenant_id, leadlane_account_id, limit=limit, offset=offset
        )

    # ------------------------------------------------------------------ #
    # Writes
    # ------------------------------------------------------------------ #

    async def save_opportunity(
        self,
        opportunity: Opportunity,
        actor: Optional[str] = None,
    ) -> Opportunity:
        """
        Persistiert eine Opportunity/Demo (Upsert in tmpl_demo_manager).
        """
        if opportunity.tenant_id is None:
            raise ValueError(
                "opportunity.tenant_id darf nicht None sein, bevor sie gespeichert wird."
            )

        # Audit
        if opportunity.created_by is None:
            opportunity.created_by = actor or "system_sync"
        opportunity.modified_by = actor or "system_sync"

        return await self._opportunities.save(opportunity)
