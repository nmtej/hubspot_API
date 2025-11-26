# app/integrations/crm/mapping/crm_contact_links_repository.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, List
from uuid import UUID

from app.integrations.crm.crm_types import CRMSystem
from app.db.database import Database


@dataclass
class CRMContactLink:
    tenant_id: UUID
    crm_system: CRMSystem
    leadlane_contact_id: str
    crm_contact_id: str


class CRMContactLinksRepository:
    """
    Link-Tabelle zwischen LeadLane-Contacts und CRM-Contacts.
    """

    def __init__(self, db: Database) -> None:
        self._db = db

    async def upsert_link(
        self,
        tenant_id: UUID,
        crm_system: CRMSystem,
        leadlane_contact_id: str,
        crm_contact_id: str,
    ) -> CRMContactLink:
        query = """
        INSERT INTO tmpl_c_db_crm_contact_links (
            tenant_id,
            crm_system,
            leadlane_contact_id,
            crm_contact_id
        )
        VALUES (:tenant_id, :crm_system, :leadlane_contact_id, :crm_contact_id)
        ON CONFLICT (tenant_id, crm_system, leadlane_contact_id)
        DO UPDATE SET crm_contact_id = EXCLUDED.crm_contact_id
        RETURNING tenant_id, crm_system, leadlane_contact_id, crm_contact_id;
        """
        row = await self._db.fetch_one(
            query,
            {
                "tenant_id": str(tenant_id),
                "crm_system": crm_system.value,
                "leadlane_contact_id": leadlane_contact_id,
                "crm_contact_id": crm_contact_id,
            },
        )
        return CRMContactLink(
            tenant_id=tenant_id,
            crm_system=crm_system,
            leadlane_contact_id=row["leadlane_contact_id"],
            crm_contact_id=row["crm_contact_id"],
        )

    async def get_by_leadlane_id(
        self,
        tenant_id: UUID,
        crm_system: CRMSystem,
        leadlane_contact_id: str,
    ) -> Optional[CRMContactLink]:
        query = """
        SELECT tenant_id, crm_system, leadlane_contact_id, crm_contact_id
        FROM tmpl_c_db_crm_contact_links
        WHERE tenant_id = :tenant_id
          AND crm_system = :crm_system
          AND leadlane_contact_id = :leadlane_contact_id;
        """
        row = await self._db.fetch_one(
            query,
            {
                "tenant_id": str(tenant_id),
                "crm_system": crm_system.value,
                "leadlane_contact_id": leadlane_contact_id,
            },
        )
        if not row:
            return None

        return CRMContactLink(
            tenant_id=tenant_id,
            crm_system=crm_system,
            leadlane_contact_id=row["leadlane_contact_id"],
            crm_contact_id=row["crm_contact_id"],
        )

    async def get_by_crm_id(
        self,
        tenant_id: UUID,
        crm_system: CRMSystem,
        crm_contact_id: str,
    ) -> Optional[CRMContactLink]:
        query = """
        SELECT tenant_id, crm_system, leadlane_contact_id, crm_contact_id
        FROM tmpl_c_db_crm_contact_links
        WHERE tenant_id = :tenant_id
          AND crm_system = :crm_system
          AND crm_contact_id = :crm_contact_id;
        """
        row = await self._db.fetch_one(
            query,
            {
                "tenant_id": str(tenant_id),
                "crm_system": crm_system.value,
                "crm_contact_id": crm_contact_id,
            },
        )
        if not row:
            return None

        return CRMContactLink(
            tenant_id=tenant_id,
            crm_system=crm_system,
            leadlane_contact_id=row["leadlane_contact_id"],
            crm_contact_id=row["crm_contact_id"],
        )

    async def list_for_tenant_and_system(
        self,
        tenant_id: UUID,
        crm_system: CRMSystem,
        limit: int = 1000,
        offset: int = 0,
    ) -> List[CRMContactLink]:
        query = """
        SELECT tenant_id, crm_system, leadlane_contact_id, crm_contact_id
        FROM tmpl_c_db_crm_contact_links
        WHERE tenant_id = :tenant_id
          AND crm_system = :crm_system
        ORDER BY leadlane_contact_id
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
            CRMContactLink(
                tenant_id=tenant_id,
                crm_system=crm_system,
                leadlane_contact_id=row["leadlane_contact_id"],
                crm_contact_id=row["crm_contact_id"],
            )
            for row in rows
        ]
