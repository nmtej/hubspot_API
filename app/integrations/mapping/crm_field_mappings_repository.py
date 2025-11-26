# app/integrations/mapping/crm_field_mappings_repository.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, List, Mapping, Optional, Iterable
from uuid import UUID

from app.db.database import Database
from app.integrations.crm.crm_types import CRMSystem


@dataclass
class CRMFieldMappingRecord:
    id: int
    tenant_id: Optional[UUID]
    crm_system: CRMSystem
    object_type: str
    udm_field: str
    crm_field: str
    is_active: bool
    direction: str = "bidirectional"  # falls später Spalte direction dazukommt


class CRMFieldMappingsRepository:
    """
    Repository für crm_field_mappings.

    Erwartete Tabelle:
        crm_field_mappings(
            id serial primary key,
            tenant_id uuid null,
            crm_system text,
            object_type text,
            udm_field_name text,
            crm_field_name text,
            is_active boolean,
            direction text null
        )
    """

    def __init__(self, db: Database) -> None:
        self._db = db

    # ------------------------------------------------------------------
    # Hilfs-Mapping Row -> Dataclass
    # ------------------------------------------------------------------

    @staticmethod
    def _row_to_record(row: Mapping[str, Any]) -> CRMFieldMappingRecord:
        return CRMFieldMappingRecord(
            id=row["id"],
            tenant_id=row.get("tenant_id"),
            crm_system=CRMSystem(row["crm_system"]),
            object_type=row["object_type"],
            udm_field=row["udm_field_name"],
            crm_field=row["crm_field_name"],
            is_active=row["is_active"],
            direction=row.get("direction") or "bidirectional",
        )

    # ------------------------------------------------------------------
    # Für MappingEngine: aktive Mappings laden
    # ------------------------------------------------------------------

    async def get_active_mappings_for_object(
        self,
        *,
        tenant_id: Optional[UUID],
        crm_system: CRMSystem,
        object_type: str,
    ) -> List[CRMFieldMappingRecord]:
        """
        Liefert aktive Mappings für (tenant_id, crm_system, object_type).

        - Berücksichtigt tenant-spezifische UND globale (tenant_id IS NULL) Mappings
        - Tenant-spezifische Mappings überschreiben globale
        """
        sql = """
        SELECT
            id,
            tenant_id,
            crm_system,
            object_type,
            udm_field_name,
            crm_field_name,
            is_active,
            direction
        FROM crm_field_mappings
        WHERE crm_system = :crm_system
          AND object_type = :object_type
          AND is_active = TRUE
          AND (
                (:tenant_id IS NOT NULL AND tenant_id = :tenant_id)
             OR (tenant_id IS NULL)
          )
        ORDER BY tenant_id NULLS FIRST, udm_field_name
        """
        rows = await self._db.fetch_all(
            sql,
            {
                "tenant_id": tenant_id,
                "crm_system": crm_system.value,
                "object_type": object_type,
            },
        )

        records = [self._row_to_record(row) for row in rows]

        # Mergen: tenant-spezifische überschreiben globale
        by_udm: dict[str, CRMFieldMappingRecord] = {}
        for rec in records:
            by_udm[rec.udm_field] = rec

        return list(by_udm.values())

    # ------------------------------------------------------------------
    # CRUD für API (Tenant + CRM)
    # ------------------------------------------------------------------

    async def list_for_tenant_and_system(
        self,
        tenant_id: UUID,
        crm_system: CRMSystem,
    ) -> list[dict]:
        sql = """
        SELECT
            id,
            tenant_id,
            crm_system,
            object_type,
            udm_field_name,
            crm_field_name,
            is_active
        FROM crm_field_mappings
        WHERE tenant_id = :tenant_id
          AND crm_system = :crm_system
        ORDER BY object_type, udm_field_name
        """
        rows = await self._db.fetch_all(
            sql,
            {"tenant_id": tenant_id, "crm_system": crm_system.value},
        )
        return [dict(row) for row in rows]

    async def create_mapping(
        self,
        tenant_id: UUID,
        crm_system: CRMSystem,
        object_type: str,
        udm_field_name: str,
        crm_field_name: str,
        is_active: bool = True,
    ) -> dict:
        sql = """
        INSERT INTO crm_field_mappings (
            tenant_id,
            crm_system,
            object_type,
            udm_field_name,
            crm_field_name,
            is_active
        )
        VALUES (
            :tenant_id,
            :crm_system,
            :object_type,
            :udm_field_name,
            :crm_field_name,
            :is_active
        )
        RETURNING
            id,
            tenant_id,
            crm_system,
            object_type,
            udm_field_name,
            crm_field_name,
            is_active
        """
        row = await self._db.fetch_one(
            sql,
            {
                "tenant_id": tenant_id,
                "crm_system": crm_system.value,
                "object_type": object_type,
                "udm_field_name": udm_field_name,
                "crm_field_name": crm_field_name,
                "is_active": is_active,
            },
        )
        return dict(row) if row else {}

    async def update_mapping(
        self,
        mapping_id: int,
        crm_field_name: str | None = None,
        is_active: bool | None = None,
    ) -> dict:
        sql = """
        UPDATE crm_field_mappings
        SET
            crm_field_name = COALESCE(:crm_field_name, crm_field_name),
            is_active = COALESCE(:is_active, is_active)
        WHERE id = :id
        RETURNING
            id,
            tenant_id,
            crm_system,
            object_type,
            udm_field_name,
            crm_field_name,
            is_active
        """
        row = await self._db.fetch_one(
            sql,
            {
                "id": mapping_id,
                "crm_field_name": crm_field_name,
                "is_active": is_active,
            },
        )
        if row is None:
            raise ValueError("mapping_not_found")
        return dict(row)

    async def delete_mapping(self, mapping_id: int) -> None:
        sql = "DELETE FROM crm_field_mappings WHERE id = :id"
        await self._db.execute(sql, {"id": mapping_id})
