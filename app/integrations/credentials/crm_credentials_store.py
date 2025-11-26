# app/integrations/credentials/crm_credentials_store.py
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Awaitable, Callable, List, Mapping, Optional
from uuid import UUID

from app.db.database import Database
from app.integrations.crm.crm_types import CRMSystem


class CRMConnectionError(Exception):
    pass


class CRMNotConnectedError(CRMConnectionError):
    def __init__(self, tenant_id: UUID, crm_system: CRMSystem) -> None:
        super().__init__(f"No active CRM connection for tenant={tenant_id}, crm_system={crm_system}")
        self.tenant_id = tenant_id
        self.crm_system = crm_system


class CRMTokenExpiredError(CRMConnectionError):
    def __init__(self, tenant_id: UUID, crm_system: CRMSystem, message: str = "") -> None:
        super().__init__(f"Token expired for tenant={tenant_id}, crm_system={crm_system}. {message}")
        self.tenant_id = tenant_id
        self.crm_system = crm_system


class CRMTokenRefreshError(CRMConnectionError):
    def __init__(self, tenant_id: UUID, crm_system: CRMSystem, message: str = "") -> None:
        super().__init__(f"Token refresh failed for tenant={tenant_id}, crm_system={crm_system}. {message}")
        self.tenant_id = tenant_id
        self.crm_system = crm_system


@dataclass
class CRMConnectionInfo:
    tenant_id: UUID
    crm_system: CRMSystem

    access_token: Optional[str]
    refresh_token: Optional[str]
    expires_at: Optional[datetime]

    token_type: Optional[str] = None
    scope: Optional[str] = None

    is_enabled: bool = True

    created_time: Optional[datetime] = None
    last_modified_time: Optional[datetime] = None
    created_by: Optional[str] = None
    modified_by: Optional[str] = None

    def is_expired(self, skew_seconds: int = 60) -> bool:
        """
        Prüft, ob das Token abgelaufen ist, mit einem kleinen Zeitpuffer.
        """
        if self.expires_at is None:
            return False
        now = datetime.now(timezone.utc)
        return self.expires_at <= now + timedelta(seconds=skew_seconds)


class CRMCredentialsStore:
    """
    Kapselt alle Zugriffe auf die CRM-Credentials-Tabelle.

    Erwartete Tabelle (Beispiel):
      crm_connections(
        tenant_id uuid,
        crm_system text,
        access_token text,
        refresh_token text,
        expires_at timestamptz,
        token_type text,
        scope text,
        is_enabled boolean,
        created_time timestamptz,
        last_modified_time timestamptz,
        created_by text,
        modified_by text,
        PRIMARY KEY (tenant_id, crm_system)
      )
    """

    def __init__(self, db: Database) -> None:
        self._db = db

    # ------------------------------------------------------------------
    # Hilfs-Mapping DB-Row -> CRMConnectionInfo
    # ------------------------------------------------------------------

    @staticmethod
    def _row_to_connection_info(row: Mapping[str, Any]) -> CRMConnectionInfo:
        return CRMConnectionInfo(
            tenant_id=row["tenant_id"],
            crm_system=CRMSystem(row["crm_system"]),
            access_token=row.get("access_token"),
            refresh_token=row.get("refresh_token"),
            expires_at=row.get("expires_at"),
            token_type=row.get("token_type"),
            scope=row.get("scope"),
            is_enabled=row.get("is_enabled", True),
            created_time=row.get("created_time"),
            last_modified_time=row.get("last_modified_time"),
            created_by=row.get("created_by"),
            modified_by=row.get("modified_by"),
        )

    # ------------------------------------------------------------------
    # Basis: einfache Credentials holen (ohne Refresh)
    # ------------------------------------------------------------------

    async def get_credentials(
        self,
        tenant_id: UUID,
        crm_system: CRMSystem | str,
    ) -> Optional[CRMConnectionInfo]:
        query = """
            SELECT
                tenant_id,
                crm_system,
                access_token,
                refresh_token,
                expires_at,
                token_type,
                scope,
                is_enabled,
                created_time,
                last_modified_time,
                created_by,
                modified_by
            FROM crm_connections
            WHERE tenant_id = :tenant_id
              AND crm_system = :crm_system
            LIMIT 1
        """
        params = {
            "tenant_id": tenant_id,
            "crm_system": crm_system.value if isinstance(crm_system, CRMSystem) else crm_system,
        }
        row = await self._db.fetch_one(query, params)
        if not row:
            return None
        return self._row_to_connection_info(row)

    # ------------------------------------------------------------------
    # Aktive Credentials inkl. Auto-Refresh
    # ------------------------------------------------------------------

    async def get_active_credentials(
        self,
        tenant_id: UUID,
        crm_system: CRMSystem | str,
        refresh_fn: Optional[Callable[[CRMConnectionInfo], Awaitable[CRMConnectionInfo]]] = None,
    ) -> CRMConnectionInfo:
        """
        Holt aktive Credentials. Falls abgelaufen:
          - wenn refresh_fn vorhanden: versucht Refresh + Persist
          - sonst: wirft CRMTokenExpiredError
        """
        system = crm_system.value if isinstance(crm_system, CRMSystem) else crm_system

        info = await self.get_credentials(tenant_id, crm_system)
        if info is None or not info.is_enabled:
            raise CRMNotConnectedError(tenant_id=tenant_id, crm_system=CRMSystem(system))

        if not info.is_expired():
            return info

        # abgelaufen
        if refresh_fn is None:
            raise CRMTokenExpiredError(
                tenant_id=tenant_id,
                crm_system=CRMSystem(system),
                message="No refresh_fn provided.",
            )

        try:
            refreshed = await refresh_fn(info)
        except Exception as exc:
            raise CRMTokenRefreshError(
                tenant_id=tenant_id,
                crm_system=CRMSystem(system),
                message=str(exc),
            ) from exc

        # persistieren
        await self.upsert_credentials(refreshed)
        return refreshed

    # ------------------------------------------------------------------
    # Upsert / Disable / List
    # ------------------------------------------------------------------

    async def upsert_credentials(self, info: CRMConnectionInfo) -> None:
        query = """
            INSERT INTO crm_connections (
                tenant_id,
                crm_system,
                access_token,
                refresh_token,
                expires_at,
                token_type,
                scope,
                is_enabled,
                created_time,
                last_modified_time,
                created_by,
                modified_by
            )
            VALUES (
                :tenant_id,
                :crm_system,
                :access_token,
                :refresh_token,
                :expires_at,
                :token_type,
                :scope,
                :is_enabled,
                :created_time,
                :last_modified_time,
                :created_by,
                :modified_by
            )
            ON CONFLICT (tenant_id, crm_system)
            DO UPDATE SET
                access_token = EXCLUDED.access_token,
                refresh_token = EXCLUDED.refresh_token,
                expires_at = EXCLUDED.expires_at,
                token_type = EXCLUDED.token_type,
                scope = EXCLUDED.scope,
                is_enabled = EXCLUDED.is_enabled,
                last_modified_time = EXCLUDED.last_modified_time,
                modified_by = EXCLUDED.modified_by
        """
        params = {
            "tenant_id": info.tenant_id,
            "crm_system": info.crm_system.value if isinstance(info.crm_system, CRMSystem) else info.crm_system,
            "access_token": info.access_token,
            "refresh_token": info.refresh_token,
            "expires_at": info.expires_at,
            "token_type": info.token_type,
            "scope": info.scope,
            "is_enabled": info.is_enabled,
            "created_time": info.created_time or datetime.now(timezone.utc),
            "last_modified_time": info.last_modified_time or datetime.now(timezone.utc),
            "created_by": info.created_by,
            "modified_by": info.modified_by,
        }
        await self._db.execute(query, params)

    async def disable_credentials(
        self,
        tenant_id: UUID,
        crm_system: CRMSystem | str,
    ) -> None:
        query = """
            UPDATE crm_connections
            SET is_enabled = FALSE,
                last_modified_time = now(),
                modified_by = 'system'
            WHERE tenant_id = :tenant_id
              AND crm_system = :crm_system
        """
        params = {
            "tenant_id": tenant_id,
            "crm_system": crm_system.value if isinstance(crm_system, CRMSystem) else crm_system,
        }
        await self._db.execute(query, params)

    async def list_connections_for_tenant(self, tenant_id: UUID) -> List[CRMConnectionInfo]:
        query = """
            SELECT
                tenant_id,
                crm_system,
                access_token,
                refresh_token,
                expires_at,
                token_type,
                scope,
                is_enabled,
                created_time,
                last_modified_time,
                created_by,
                modified_by
            FROM crm_connections
            WHERE tenant_id = :tenant_id
        """
        rows = await self._db.fetch_all(query, {"tenant_id": tenant_id})
        return [self._row_to_connection_info(row) for row in rows]

    async def list_connected_systems(self, tenant_id: UUID) -> List[CRMSystem]:
        """
        Liefert alle CRM-Systeme zurück, für die der Tenant eine
        aktive (is_enabled) Verbindung hat.
        """
        connections = await self.list_connections_for_tenant(tenant_id)
        systems: List[CRMSystem] = []
        for conn in connections:
            if conn.is_enabled and conn.crm_system not in systems:
                systems.append(conn.crm_system)
        return systems
