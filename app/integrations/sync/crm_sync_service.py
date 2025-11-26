# app/integrations/sync/crm_sync_service.py

from __future__ import annotations

import logging
from typing import Optional, Union
from uuid import UUID

from app.integrations.crm.crm_types import (
    CRMSystem,
    CRMCompanyPayload,
    CRMContactPayload,
    CRMDealPayload,
    CRMActivityPayload,
    CRMSyncResult,
    CRMSyncError,
)
from app.integrations.crm.crm_client_factory import create_crm_client
from app.integrations.credentials.crm_credentials_store import (
    CRMCredentialsStore,
    CRMConnectionError,
)
from app.integrations.mapping import (
    CRMFieldMappingEngine,
    CRMAccountLinksRepository,
    CRMContactLinksRepository,
    CRMOpportunityLinksRepository,
)

logger = logging.getLogger(__name__)


TenantId = Union[str, UUID]


def _as_uuid(value: TenantId) -> UUID:
    if isinstance(value, UUID):
        return value
    return UUID(str(value))


class CRMSyncService:
    """
    Verantwortlich für den Outbound-Sync vom UDM ins jeweilige CRM.

    Aufgaben:
    - Sicherstellen, dass ein Tenant für das CRM korrekt verbunden ist (Credentials vorhanden).
    - Vorhandene Links (LeadLane-ID <-> CRM-ID) nutzen bzw. anlegen/updaten.
    - CRM-Client erzeugen und Upsert ausführen.
    - CRMSyncResult/CRMSyncError sauber zurückgeben.
    """

    def __init__(
        self,
        credentials_store: CRMCredentialsStore,
        mapping_engine: CRMFieldMappingEngine,
        account_links_repo: CRMAccountLinksRepository,
        contact_links_repo: CRMContactLinksRepository,
        opportunity_links_repo: CRMOpportunityLinksRepository,
        activity_links_repo: Optional[object] = None,
    ) -> None:
        self._credentials_store = credentials_store
        self._mapping_engine = mapping_engine
        self._account_links_repo = account_links_repo
        self._contact_links_repo = contact_links_repo
        self._opportunity_links_repo = opportunity_links_repo
        self._activity_links_repo = activity_links_repo

    # -------------------------------------------------------------------------
    # Public API
    # -------------------------------------------------------------------------

    async def sync_company_to_crm(
        self,
        tenant_id: TenantId,
        crm_system: CRMSystem,
        payload: CRMCompanyPayload,
    ) -> CRMSyncResult:
        """
        Synchronisiert eine Company (Account) in ein bestimmtes CRM.
        """
        leadlane_id = payload.leadlane_sub_company_id

        logger.info(
            "Starting company sync: tenant_id=%s, crm_system=%s, leadlane_company_id=%s",
            tenant_id,
            crm_system.value,
            leadlane_id,
        )

        # 1) Basis-Validierung
        if not leadlane_id:
            return self._simple_error_result(
                crm_system=crm_system,
                object_type="company",
                leadlane_id=None,
                code="missing_leadlane_id",
                message="CRMCompanyPayload.leadlane_sub_company_id ist erforderlich.",
            )

        # 2) Credentials prüfen / laden
        credentials_ok = await self._ensure_credentials(
            tenant_id, crm_system, object_type="company", leadlane_id=leadlane_id
        )
        if isinstance(credentials_ok, CRMSyncResult):
            # Im Fehlerfall geben wir direkt das Result zurück
            return credentials_ok

        # 3) CRM-Client erzeugen
        client = create_crm_client(
            crm_system=crm_system,
            tenant_id=str(tenant_id),
            credentials_store=self._credentials_store,
            mapping_engine=self._mapping_engine,
        )

        # 4) Vorhandenen Link holen (falls schon einmal synchronisiert)
        # nutzt DEIN Repo: get_by_leadlane_id(.., leadlane_sub_company_id)
        tenant_uuid = _as_uuid(tenant_id)
        existing_link = await self._account_links_repo.get_by_leadlane_id(
            tenant_id=tenant_uuid,
            crm_system=crm_system,
            leadlane_sub_company_id=leadlane_id,
        )
        # Feldname aus deinem Dataclass: crm_account_id
        existing_crm_id: Optional[str] = (
            existing_link.crm_account_id if existing_link else None
        )

        # 5) Upsert ausführen
        try:
            result = await client.upsert_company(
                payload=payload,
                existing_crm_id=existing_crm_id,
            )
        except Exception as exc:  # noqa: BLE001
            logger.exception(
                "Error while upserting company to CRM: tenant_id=%s, crm_system=%s, leadlane_company_id=%s",
                tenant_id,
                crm_system.value,
                leadlane_id,
            )
            return self._simple_error_result(
                crm_system=crm_system,
                object_type="company",
                leadlane_id=leadlane_id,
                code="crm_client_error",
                message="Unerwarteter Fehler beim Upsert der Company im CRM.",
                details={"exception": repr(exc)},
            )

        # 6) Link updaten/erstellen, wenn Upsert erfolgreich
        await self._handle_link_update_for_company(
            tenant_id=tenant_id,
            crm_system=crm_system,
            leadlane_company_id=leadlane_id,
            existing_link_id=None,  # wir nutzen upsert_link, ID ist egal
            result=result,
        )

        logger.info(
            "Finished company sync: tenant_id=%s, crm_system=%s, leadlane_company_id=%s, success=%s",
            tenant_id,
            crm_system.value,
            leadlane_id,
            result.success,
        )
        return result

    async def sync_contact_to_crm(
        self,
        tenant_id: TenantId,
        crm_system: CRMSystem,
        payload: CRMContactPayload,
    ) -> CRMSyncResult:
        """
        Synchronisiert einen Contact in ein bestimmtes CRM.
        """
        leadlane_id = payload.leadlane_contact_id

        logger.info(
            "Starting contact sync: tenant_id=%s, crm_system=%s, leadlane_contact_id=%s",
            tenant_id,
            crm_system.value,
            leadlane_id,
        )

        if not leadlane_id:
            return self._simple_error_result(
                crm_system=crm_system,
                object_type="contact",
                leadlane_id=None,
                code="missing_leadlane_id",
                message="CRMContactPayload.leadlane_contact_id ist erforderlich.",
            )

        credentials_ok = await self._ensure_credentials(
            tenant_id, crm_system, object_type="contact", leadlane_id=leadlane_id
        )
        if isinstance(credentials_ok, CRMSyncResult):
            return credentials_ok

        client = create_crm_client(
            crm_system=crm_system,
            tenant_id=str(tenant_id),
            credentials_store=self._credentials_store,
            mapping_engine=self._mapping_engine,
        )

        tenant_uuid = _as_uuid(tenant_id)
        existing_link = await self._contact_links_repo.get_by_leadlane_id(
            tenant_id=tenant_uuid,
            crm_system=crm_system,
            leadlane_contact_id=leadlane_id,
        )
        existing_crm_id: Optional[str] = (
            existing_link.crm_contact_id if existing_link else None
        )

        try:
            result = await client.upsert_contact(
                payload=payload,
                existing_crm_id=existing_crm_id,
            )
        except Exception as exc:  # noqa: BLE001
            logger.exception(
                "Error while upserting contact to CRM: tenant_id=%s, crm_system=%s, leadlane_contact_id=%s",
                tenant_id,
                crm_system.value,
                leadlane_id,
            )
            return self._simple_error_result(
                crm_system=crm_system,
                object_type="contact",
                leadlane_id=leadlane_id,
                code="crm_client_error",
                message="Unerwarteter Fehler beim Upsert des Kontakts im CRM.",
                details={"exception": repr(exc)},
            )

        await self._handle_link_update_for_contact(
            tenant_id=tenant_id,
            crm_system=crm_system,
            leadlane_contact_id=leadlane_id,
            existing_link_id=None,
            result=result,
        )

        logger.info(
            "Finished contact sync: tenant_id=%s, crm_system=%s, leadlane_contact_id=%s, success=%s",
            tenant_id,
            crm_system.value,
            leadlane_id,
            result.success,
        )
        return result

    async def sync_opportunity_to_crm(
        self,
        tenant_id: TenantId,
        crm_system: CRMSystem,
        payload: CRMDealPayload,
    ) -> CRMSyncResult:
        """
        Synchronisiert eine Opportunity (Deal) in ein bestimmtes CRM.
        """
        leadlane_id = payload.leadlane_opportunity_id

        logger.info(
            "Starting opportunity sync: tenant_id=%s, crm_system=%s, leadlane_opportunity_id=%s",
            tenant_id,
            crm_system.value,
            leadlane_id,
        )

        if not leadlane_id:
            return self._simple_error_result(
                crm_system=crm_system,
                object_type="opportunity",
                leadlane_id=None,
                code="missing_leadlane_id",
                message="CRMDealPayload.leadlane_opportunity_id ist erforderlich.",
            )

        credentials_ok = await self._ensure_credentials(
            tenant_id, crm_system, object_type="opportunity", leadlane_id=leadlane_id
        )
        if isinstance(credentials_ok, CRMSyncResult):
            return credentials_ok

        client = create_crm_client(
            crm_system=crm_system,
            tenant_id=str(tenant_id),
            credentials_store=self._credentials_store,
            mapping_engine=self._mapping_engine,
        )

        tenant_uuid = _as_uuid(tenant_id)
        # dein Repo heißt leadlane_demo_id – wir verwenden die Opportunity-ID dafür
        existing_link = await self._opportunity_links_repo.get_by_leadlane_id(
            tenant_id=tenant_uuid,
            crm_system=crm_system,
            leadlane_demo_id=leadlane_id,
        )
        existing_crm_id: Optional[str] = (
            existing_link.crm_opportunity_id if existing_link else None
        )

        try:
            result = await client.upsert_deal(
                payload=payload,
                existing_crm_id=existing_crm_id,
            )
        except Exception as exc:  # noqa: BLE001
            logger.exception(
                "Error while upserting opportunity to CRM: tenant_id=%s, crm_system=%s, leadlane_opportunity_id=%s",
                tenant_id,
                crm_system.value,
                leadlane_id,
            )
            return self._simple_error_result(
                crm_system=crm_system,
                object_type="opportunity",
                leadlane_id=leadlane_id,
                code="crm_client_error",
                message="Unerwarteter Fehler beim Upsert der Opportunity im CRM.",
                details={"exception": repr(exc)},
            )

        await self._handle_link_update_for_opportunity(
            tenant_id=tenant_id,
            crm_system=crm_system,
            leadlane_opportunity_id=leadlane_id,
            existing_link_id=None,
            result=result,
        )

        logger.info(
            "Finished opportunity sync: tenant_id=%s, crm_system=%s, leadlane_opportunity_id=%s, success=%s",
            tenant_id,
            crm_system.value,
            leadlane_id,
            result.success,
        )
        return result

    async def sync_activity_to_crm(
        self,
        tenant_id: TenantId,
        crm_system: CRMSystem,
        payload: CRMActivityPayload,
    ) -> CRMSyncResult:
        """
        Synchronisiert eine Aktivität (Call, Mail, Task, etc.) in ein bestimmtes CRM.
        """
        leadlane_id = payload.leadlane_activity_id

        logger.info(
            "Starting activity sync: tenant_id=%s, crm_system=%s, leadlane_activity_id=%s",
            tenant_id,
            crm_system.value,
            leadlane_id,
        )

        if not leadlane_id:
            return self._simple_error_result(
                crm_system=crm_system,
                object_type="activity",
                leadlane_id=None,
                code="missing_leadlane_id",
                message="CRMActivityPayload.leadlane_activity_id ist erforderlich.",
            )

        credentials_ok = await self._ensure_credentials(
            tenant_id, crm_system, object_type="activity", leadlane_id=leadlane_id
        )
        if isinstance(credentials_ok, CRMSyncResult):
            return credentials_ok

        if not self._activity_links_repo:
            # Falls du Activities (noch) nicht verlinkst, trotzdem ins CRM schreiben
            logger.debug("No activity_links_repo configured – skipping link handling.")

        client = create_crm_client(
            crm_system=crm_system,
            tenant_id=str(tenant_id),
            credentials_store=self._credentials_store,
            mapping_engine=self._mapping_engine,
        )

        existing_link = None
        if self._activity_links_repo:
            tenant_uuid = _as_uuid(tenant_id)
            # hier musst du schauen, wie dein Activity-Link-Repo heißt – ich gehe von get_by_leadlane_id aus
            existing_link = await self._activity_links_repo.get_by_leadlane_id(
                tenant_id=tenant_uuid,
                crm_system=crm_system,
                leadlane_activity_id=leadlane_id,
            )

        # analog: crm_activity_id o.ä., je nach Dataclass
        existing_crm_id: Optional[str] = (
            getattr(existing_link, "crm_activity_id", None) if existing_link else None
        )

        try:
            result = await client.upsert_activity(
                payload=payload,
                existing_crm_id=existing_crm_id,
            )
        except Exception as exc:  # noqa: BLE001
            logger.exception(
                "Error while upserting activity to CRM: tenant_id=%s, crm_system=%s, leadlane_activity_id=%s",
                tenant_id,
                crm_system.value,
                leadlane_id,
            )
            return self._simple_error_result(
                crm_system=crm_system,
                object_type="activity",
                leadlane_id=leadlane_id,
                code="crm_client_error",
                message="Unerwarteter Fehler beim Upsert der Aktivität im CRM.",
                details={"exception": repr(exc)},
            )

        if self._activity_links_repo:
            await self._handle_link_update_for_activity(
                tenant_id=tenant_id,
                crm_system=crm_system,
                leadlane_activity_id=leadlane_id,
                existing_link_id=None,
                result=result,
            )

        logger.info(
            "Finished activity sync: tenant_id=%s, crm_system=%s, leadlane_activity_id=%s, success=%s",
            tenant_id,
            crm_system.value,
            leadlane_id,
            result.success,
        )
        return result

    # -------------------------------------------------------------------------
    # Helpers: Credentials, Fehler, Link-Handling
    # -------------------------------------------------------------------------

    async def _ensure_credentials(
        self,
        tenant_id: TenantId,
        crm_system: CRMSystem,
        object_type: str,
        leadlane_id: Optional[str] = None,
    ) -> Optional[CRMSyncResult]:
        """
        Prüft, ob für den Tenant/CRM gültige Credentials vorhanden sind.

        Gibt:
        - None, wenn alles ok
        - CRMSyncResult mit Fehler, wenn nicht
        """
        try:
            conn = await self._credentials_store.get_credentials(tenant_id, crm_system)
        except CRMConnectionError as exc:
            logger.warning(
                "No CRM credentials for sync: tenant_id=%s, crm_system=%s, object_type=%s, leadlane_id=%s, error=%s",
                tenant_id,
                crm_system.value,
                object_type,
                leadlane_id,
                exc,
            )
            return self._simple_error_result(
                crm_system=crm_system,
                object_type=object_type,
                leadlane_id=leadlane_id,
                code="missing_credentials",
                message=f"Keine aktiven Credentials für {crm_system.value} vorhanden.",
                details={"error": str(exc)},
            )

        if not conn.is_enabled:
            logger.warning(
                "CRM connection disabled: tenant_id=%s, crm_system=%s, object_type=%s, leadlane_id=%s",
                tenant_id,
                crm_system.value,
                object_type,
                leadlane_id,
            )
            return self._simple_error_result(
                crm_system=crm_system,
                object_type=object_type,
                leadlane_id=leadlane_id,
                code="connection_disabled",
                message=f"Die Verbindung zu {crm_system.value} ist für diesen Tenant deaktiviert.",
            )

        return None

    def _simple_error_result(
        self,
        crm_system: CRMSystem,
        object_type: str,
        leadlane_id: Optional[str],
        code: str,
        message: str,
        details: Optional[dict] = None,
    ) -> CRMSyncResult:
        return CRMSyncResult(
            success=False,
            crm_system=crm_system,
            crm_object_type=object_type,
            crm_id=None,
            leadlane_id=leadlane_id,
            errors=[
                CRMSyncError(
                    code=code,
                    message=message,
                    details=details or {},
                )
            ],
            raw_response=None,
        )

    async def _handle_link_update_for_company(
        self,
        tenant_id: TenantId,
        crm_system: CRMSystem,
        leadlane_company_id: str,
        existing_link_id: Optional[int],
        result: CRMSyncResult,
    ) -> None:
        if not result.success or not result.crm_id:
            logger.debug(
                "Skipping company link update – sync not successful or missing crm_id. tenant_id=%s, crm_system=%s, leadlane_company_id=%s",
                tenant_id,
                crm_system.value,
                leadlane_company_id,
            )
            return

        # Variante A: immer upsert_link – dein Repo kümmert sich um INSERT/UPDATE
        tenant_uuid = _as_uuid(tenant_id)
        await self._account_links_repo.upsert_link(
            tenant_id=tenant_uuid,
            crm_system=crm_system,
            leadlane_sub_company_id=leadlane_company_id,
            crm_account_id=result.crm_id,
        )

    async def _handle_link_update_for_contact(
        self,
        tenant_id: TenantId,
        crm_system: CRMSystem,
        leadlane_contact_id: str,
        existing_link_id: Optional[int],
        result: CRMSyncResult,
    ) -> None:
        if not result.success or not result.crm_id:
            logger.debug(
                "Skipping contact link update – sync not successful or missing crm_id. tenant_id=%s, crm_system=%s, leadlane_contact_id=%s",
                tenant_id,
                crm_system.value,
                leadlane_contact_id,
            )
            return

        tenant_uuid = _as_uuid(tenant_id)
        await self._contact_links_repo.upsert_link(
            tenant_id=tenant_uuid,
            crm_system=crm_system,
            leadlane_contact_id=leadlane_contact_id,
            crm_contact_id=result.crm_id,
        )

    async def _handle_link_update_for_opportunity(
        self,
        tenant_id: TenantId,
        crm_system: CRMSystem,
        leadlane_opportunity_id: str,
        existing_link_id: Optional[int],
        result: CRMSyncResult,
    ) -> None:
        if not result.success or not result.crm_id:
            logger.debug(
                "Skipping opportunity link update – sync not successful or missing crm_id. tenant_id=%s, crm_system=%s, leadlane_opportunity_id=%s",
                tenant_id,
                crm_system.value,
                leadlane_opportunity_id,
            )
            return

        tenant_uuid = _as_uuid(tenant_id)
        await self._opportunity_links_repo.upsert_link(
            tenant_id=tenant_uuid,
            crm_system=crm_system,
            # deine Tabelle nutzt leadlane_demo_id als Schlüssel
            leadlane_demo_id=leadlane_opportunity_id,
            crm_opportunity_id=result.crm_id,
        )

    async def _handle_link_update_for_activity(
        self,
        tenant_id: TenantId,
        crm_system: CRMSystem,
        leadlane_activity_id: str,
        existing_link_id: Optional[int],
        result: CRMSyncResult,
    ) -> None:
        if not result.success or not result.crm_id or not self._activity_links_repo:
            logger.debug(
                "Skipping activity link update – sync not successful, missing crm_id or no repo. tenant_id=%s, crm_system=%s, leadlane_activity_id=%s",
                tenant_id,
                crm_system.value,
                leadlane_activity_id,
            )
            return

        tenant_uuid = _as_uuid(tenant_id)
        await self._activity_links_repo.upsert_link(
            tenant_id=tenant_uuid,
            crm_system=crm_system,
            leadlane_activity_id=leadlane_activity_id,
            crm_activity_id=result.crm_id,
        )
