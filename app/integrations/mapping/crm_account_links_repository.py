# app/integrations/crm/mapping/crm_account_links_repository.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, List
from uuid import UUID

from app.integrations.crm.crm_types import CRMSystem
from app.db.database import Database


@dataclass
class CRMAccountLink:
    tenant_id: UUID
    crm_system: CRMSystem
    leadlane_sub_company_id: str
    crm_account_id: str


class CRMAccountLinksRepository:
    """
    Verwaltet Link-Tabelle zwischen LeadLane-Company (sub_company) und CRM-Accounts.
    """

    def __init__(self, db: Database) -> None:
        self._db = db

    async def upsert_link(
        self,
        tenant_id: UUID,
        crm_system: CRMSystem,
        leadlane_sub_company_id: str,
        crm_account_id: str,
    ) -> CRMAccountLink:
        """
        Speichert oder aktualisiert den Link zwischen LeadLane-Company und CRM-Account.
        """
        query = """
        INSERT INTO tmpl_c_db_crm_account_links (
            tenant_id,
            crm_system,
            leadlane_sub_company_id,
            crm_account_id
        )
        VALUES (:tenant_id, :crm_system, :leadlane_sub_company_id, :crm_account_id)
        ON CONFLICT (tenant_id, crm_system, leadlane_sub_company_id)
        DO UPDATE SET crm_account_id = EXCLUDED.crm_account_id
        RETURNING tenant_id, crm_system, leadlane_sub_company_id, crm_account_id;
        """
        row = await self._db.fetch_one(
            query,
            {
                "tenant_id": str(tenant_id),
                "crm_system": crm_system.value,
                "leadlane_sub_company_id": leadlane_sub_company_id,
                "crm_account_id": crm_account_id,
            },
        )
        return CRMAccountLink(
            tenant_id=tenant_id,
            crm_system=crm_system,
            leadlane_sub_company_id=row["leadlane_sub_company_id"],
            crm_account_id=row["crm_account_id"],
        )

    async def get_by_leadlane_id(
        self,
        tenant_id: UUID,
        crm_system: CRMSystem,
        leadlane_sub_company_id: str,
    ) -> Optional[CRMAccountLink]:
        query = """
        SELECT tenant_id, crm_system, leadlane_sub_company_id, crm_account_id
        FROM tmpl_c_db_crm_account_links
        WHERE tenant_id = :tenant_id
          AND crm_system = :crm_system
          AND leadlane_sub_company_id = :leadlane_sub_company_id;
        """
        row = await self._db.fetch_one(
            query,
            {
                "tenant_id": str(tenant_id),
                "crm_system": crm_system.value,
                "leadlane_sub_company_id": leadlane_sub_company_id,
            },
        )
        if not row:
            return None

        return CRMAccountLink(
            tenant_id=tenant_id,
            crm_system=crm_system,
            leadlane_sub_company_id=row["leadlane_sub_company_id"],
            crm_account_id=row["crm_account_id"],
        )

    async def get_by_crm_id(
        self,
        tenant_id: UUID,
        crm_system: CRMSystem,
        crm_account_id: str,
    ) -> Optional[CRMAccountLink]:
        query = """
        SELECT tenant_id, crm_system, leadlane_sub_company_id, crm_account_id
        FROM tmpl_c_db_crm_account_links
        WHERE tenant_id = :tenant_id
          AND crm_system = :crm_system
          AND crm_account_id = :crm_account_id;
        """
        row = await self._db.fetch_one(
            query,
            {
                "tenant_id": str(tenant_id),
                "crm_system": crm_system.value,
                "crm_account_id": crm_account_id,
            },
        )
        if not row:
            return None

        return CRMAccountLink(
            tenant_id=tenant_id,
            crm_system=crm_system,
            leadlane_sub_company_id=row["leadlane_sub_company_id"],
            crm_account_id=row["crm_account_id"],
        )

    async def list_for_tenant_and_system(
        self,
        tenant_id: UUID,
        crm_system: CRMSystem,
        limit: int = 1000,
        offset: int = 0,
    ) -> List[CRMAccountLink]:
        query = """
        SELECT tenant_id, crm_system, leadlane_sub_company_id, crm_account_id
        FROM tmpl_c_db_crm_account_links
        WHERE tenant_id = :tenant_id
          AND crm_system = :crm_system
        ORDER BY leadlane_sub_company_id
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
            CRMAccountLink(
                tenant_id=tenant_id,
                crm_system=crm_system,
                leadlane_sub_company_id=row["leadlane_sub_company_id"],
                crm_account_id=row["crm_account_id"],
            )
            for row in rows
        ]
