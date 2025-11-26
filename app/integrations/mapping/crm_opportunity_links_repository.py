# app/integrations/crm/mapping/crm_opportunity_links_repository.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, List
from uuid import UUID

from app.integrations.crm.crm_types import CRMSystem
from app.db.database import Database


@dataclass
class CRMOpportunityLink:
    tenant_id: UUID
    crm_system: CRMSystem
    leadlane_demo_id: str  # oder allgemeiner: leadlane_opportunity_id
    crm_opportunity_id: str


class CRMOpportunityLinksRepository:
    """
    Link-Tabelle zwischen LeadLane-Demos/Opportunities und CRM-Opportunities/Deals.
    """

    def __init__(self, db: Database) -> None:
        self._db = db

    async def upsert_link(
        self,
        tenant_id: UUID,
        crm_system: CRMSystem,
        leadlane_demo_id: str,
        crm_opportunity_id: str,
    ) -> CRMOpportunityLink:
        query = """
        INSERT INTO tmpl_c_db_crm_opportunity_links (
            tenant_id,
            crm_system,
            leadlane_demo_id,
            crm_opportunity_id
        )
        VALUES (:tenant_id, :crm_system, :leadlane_demo_id, :crm_opportunity_id)
        ON CONFLICT (tenant_id, crm_system, leadlane_demo_id)
        DO UPDATE SET crm_opportunity_id = EXCLUDED.crm_opportunity_id
        RETURNING tenant_id, crm_system, leadlane_demo_id, crm_opportunity_id;
        """
        row = await self._db.fetch_one(
            query,
            {
                "tenant_id": str(tenant_id),
                "crm_system": crm_system.value,
                "leadlane_demo_id": leadlane_demo_id,
                "crm_opportunity_id": crm_opportunity_id,
            },
        )
        return CRMOpportunityLink(
            tenant_id=tenant_id,
            crm_system=crm_system,
            leadlane_demo_id=row["leadlane_demo_id"],
            crm_opportunity_id=row["crm_opportunity_id"],
        )

    async def get_by_leadlane_id(
        self,
        tenant_id: UUID,
        crm_system: CRMSystem,
        leadlane_demo_id: str,
    ) -> Optional[CRMOpportunityLink]:
        query = """
        SELECT tenant_id, crm_system, leadlane_demo_id, crm_opportunity_id
        FROM tmpl_c_db_crm_opportunity_links
        WHERE tenant_id = :tenant_id
          AND crm_system = :crm_system
          AND leadlane_demo_id = :leadlane_demo_id;
        """
        row = await self._db.fetch_one(
            query,
            {
                "tenant_id": str(tenant_id),
                "crm_system": crm_system.value,
                "leadlane_demo_id": leadlane_demo_id,
            },
        )
        if not row:
            return None

        return CRMOpportunityLink(
            tenant_id=tenant_id,
            crm_system=crm_system,
            leadlane_demo_id=row["leadlane_demo_id"],
            crm_opportunity_id=row["crm_opportunity_id"],
        )

    async def get_by_crm_id(
        self,
        tenant_id: UUID,
        crm_system: CRMSystem,
        crm_opportunity_id: str,
    ) -> Optional[CRMOpportunityLink]:
        query = """
        SELECT tenant_id, crm_system, leadlane_demo_id, crm_opportunity_id
        FROM tmpl_c_db_crm_opportunity_links
        WHERE tenant_id = :tenant_id
          AND crm_system = :crm_system
          AND crm_opportunity_id = :crm_opportunity_id;
        """
        row = await self._db.fetch_one(
            query,
            {
                "tenant_id": str(tenant_id),
                "crm_system": crm_system.value,
                "crm_opportunity_id": crm_opportunity_id,
            },
        )
        if not row:
            return None

        return CRMOpportunityLink(
            tenant_id=tenant_id,
            crm_system=crm_system,
            leadlane_demo_id=row["leadlane_demo_id"],
            crm_opportunity_id=row["crm_opportunity_id"],
        )

    async def list_for_tenant_and_system(
        self,
        tenant_id: UUID,
        crm_system: CRMSystem,
        limit: int = 1000,
        offset: int = 0,
    ) -> List[CRMOpportunityLink]:
        query = """
        SELECT tenant_id, crm_system, leadlane_demo_id, crm_opportunity_id
        FROM tmpl_c_db_crm_opportunity_links
        WHERE tenant_id = :tenant_id
          AND crm_system = :crm_system
        ORDER BY leadlane_demo_id
        LIMIT :limit OFFSET :offset;
        """
        rows = await self._db.fetch_all(
            query,
            {
                "tenant_id": str(tenant_id),
                "crm_system": crm_system.value,
                "limit": limit,
                "offset": offset,
            },
        )
        return [
            CRMOpportunityLink(
                tenant_id=tenant_id,
                crm_system=crm_system,
                leadlane_demo_id=row["leadlane_demo_id"],
                crm_opportunity_id=row["crm_opportunity_id"],
            )
            for row in rows
        ]
