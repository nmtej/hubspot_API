# app/domain/repositories/opportunity_repository.py
from __future__ import annotations

from typing import Optional, Sequence, Mapping, Any
from uuid import UUID

from app.domain.models.opportunity import Opportunity
from app.db.database import Database  # dein DB-Wrapper (fetch_one, fetch_all, execute)


class OpportunityRepository:
    """
    Konkretes Opportunity-Repository für Supabase/Postgres.

    Nutzt:
      - public.tmpl_demo_manager

    Domain-Model:
      - Opportunity mit:
        - leadlane_sub_company_id (Domain-Name)
        - demo_preparation (Domain-Name)

    DB-Realität:
      - Spalten:
        - leadlane_account_id
        - demo_preperation  (mit Schreibfehler)
    """

    def __init__(self, db: Database) -> None:
        self._db = db

    # -------------------------------------------------------------------------
    # Public API
    # -------------------------------------------------------------------------

    async def get(
        self,
        tenant_id: UUID,
        leadlane_demo_id: UUID,
    ) -> Optional[Opportunity]:
        row = await self._db.fetch_one(
            _SELECT_OPPORTUNITY_BY_ID_SQL,
            {"leadlane_demo_id": str(leadlane_demo_id)},
        )
        if row is None:
            return None

        return self._row_to_opportunity(row, tenant_id=tenant_id)

    async def list_for_account(
        self,
        tenant_id: UUID,
        leadlane_sub_company_id: UUID,
        limit: int = 100,
        offset: int = 0,
    ) -> Sequence[Opportunity]:
        """
        Listet Opportunities für einen Account (Company/SubCompany).

        Domain:
          - leadlane_sub_company_id

        DB:
          - leadlane_account_id
        """
        rows = await self._db.fetch_all(
            _SELECT_OPPORTUNITIES_FOR_ACCOUNT_SQL,
            {
                "leadlane_account_id": str(leadlane_sub_company_id),
                "limit": limit,
                "offset": offset,
            },
        )
        return [self._row_to_opportunity(r, tenant_id=tenant_id) for r in rows]

    async def save(self, opportunity: Opportunity) -> Opportunity:
        """
        Upsert einer Opportunity/Demo in tmpl_demo_manager.

        Domain:
          - opportunity.leadlane_sub_company_id
          - opportunity.demo_preparation

        DB:
          - leadlane_account_id
          - demo_preperation

        Audit:
          - created_time/last_modified_time kommen aus der DB (DEFAULT/now()).
          - created_by/modified_by kommen aus dem Service (actor).
        """
        await self._db.execute(
            _UPSERT_OPPORTUNITY_SQL,
            {
                "leadlane_demo_id": str(opportunity.leadlane_demo_id),
                "leadlane_account_id": str(opportunity.leadlane_sub_company_id),
                "leadlane_contact_id": str(opportunity.leadlane_contact_id),
                "responsible_sdr_id": (
                    str(opportunity.responsible_sdr_id)
                    if opportunity.responsible_sdr_id
                    else None
                ),
                "demo_date": opportunity.demo_date,
                "demo_invite_sent_at": opportunity.demo_invite_sent_at,
                "demo_preperation": opportunity.demo_preparation,
                "demo_status": opportunity.demo_status,
                "bant_budget": opportunity.bant_budget,
                "bant_authority": opportunity.bant_authority,
                "bant_need": opportunity.bant_need,
                "bant_timing": opportunity.bant_timing,
                "bant_comment": opportunity.bant_comment,
                "created_by": opportunity.created_by,
                "modified_by": opportunity.modified_by,
            },
        )
        return opportunity

    # -------------------------------------------------------------------------
    # Row → Domain Mapping
    # -------------------------------------------------------------------------

    def _row_to_opportunity(
        self,
        row: Mapping[str, Any],
        tenant_id: UUID,
    ) -> Opportunity:
        """
        Mappt eine DB-Zeile aus tmpl_demo_manager auf das Opportunity-UDM.

        Domain:
          - leadlane_sub_company_id  ←  row["leadlane_account_id"]
          - demo_preparation         ←  row["demo_preperation"]
        """
        return Opportunity(
            tenant_id=tenant_id,
            leadlane_demo_id=row["leadlane_demo_id"],
            leadlane_sub_company_id=row["leadlane_account_id"],
            leadlane_contact_id=row["leadlane_contact_id"],
            responsible_sdr_id=row.get("responsible_sdr_id"),
            demo_date=row.get("demo_date"),
            demo_invite_sent_at=row.get("demo_invite_sent_at"),
            demo_preparation=row.get("demo_preperation"),
            demo_status=row.get("demo_status"),
            bant_budget=row.get("bant_budget", "unknown"),
            bant_authority=row.get("bant_authority", "unknown"),
            bant_need=row.get("bant_need", "unknown"),
            bant_timing=row.get("bant_timing", "unknown"),
            bant_comment=row.get("bant_comment"),
            created_time=row.get("created_time"),
            last_modified_time=row.get("last_modified_time"),
            created_by=row.get("created_by"),
            modified_by=row.get("modified_by"),
        )


# -------------------------------------------------------------------------
# SQL-Statements
# -------------------------------------------------------------------------

_SELECT_OPPORTUNITY_BY_ID_SQL = """
    SELECT
        leadlane_demo_id,
        leadlane_account_id,
        leadlane_contact_id,
        responsible_sdr_id,
        demo_date,
        demo_invite_sent_at,
        demo_preperation,
        demo_status,
        bant_budget,
        bant_authority,
        bant_need,
        bant_timing,
        bant_comment,
        created_time,
        last_modified_time,
        created_by,
        modified_by
    FROM public.tmpl_demo_manager
    WHERE leadlane_demo_id = :leadlane_demo_id
"""

_SELECT_OPPORTUNITIES_FOR_ACCOUNT_SQL = """
    SELECT
        leadlane_demo_id,
        leadlane_account_id,
        leadlane_contact_id,
        responsible_sdr_id,
        demo_date,
        demo_invite_sent_at,
        demo_preperation,
        demo_status,
        bant_budget,
        bant_authority,
        bant_need,
        bant_timing,
        bant_comment,
        created_time,
        last_modified_time,
        created_by,
        modified_by
    FROM public.tmpl_demo_manager
    WHERE leadlane_account_id = :leadlane_account_id
    ORDER BY created_time DESC
    LIMIT :limit OFFSET :offset
"""

_UPSERT_OPPORTUNITY_SQL = """
    INSERT INTO public.tmpl_demo_manager (
        leadlane_demo_id,
        leadlane_account_id,
        leadlane_contact_id,
        responsible_sdr_id,
        demo_date,
        demo_invite_sent_at,
        demo_preperation,
        demo_status,
        bant_budget,
        bant_authority,
        bant_need,
        bant_timing,
        bant_comment,
        created_by,
        modified_by
    )
    VALUES (
        :leadlane_demo_id,
        :leadlane_account_id,
        :leadlane_contact_id,
        :responsible_sdr_id,
        :demo_date,
        :demo_invite_sent_at,
        :demo_preperation,
        :demo_status,
        :bant_budget,
        :bant_authority,
        :bant_need,
        :bant_timing,
        :bant_comment,
        :created_by,
        :modified_by
    )
    ON CONFLICT (leadlane_demo_id)
    DO UPDATE SET
        leadlane_account_id = EXCLUDED.leadlane_account_id,
        leadlane_contact_id = EXCLUDED.leadlane_contact_id,
        responsible_sdr_id = EXCLUDED.responsible_sdr_id,
        demo_date = EXCLUDED.demo_date,
        demo_invite_sent_at = EXCLUDED.demo_invite_sent_at,
        demo_preperation = EXCLUDED.demo_preperation,
        demo_status = EXCLUDED.demo_status,
        bant_budget = EXCLUDED.bant_budget,
        bant_authority = EXCLUDED.bant_authority,
        bant_need = EXCLUDED.bant_need,
        bant_timing = EXCLUDED.bant_timing,
        bant_comment = EXCLUDED.bant_comment,
        last_modified_time = now(),
        modified_by = EXCLUDED.modified_by
"""
