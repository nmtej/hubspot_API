# app/integrations/sync/crm_sync_listener.py
from __future__ import annotations

import asyncio
import logging
from typing import Dict, TYPE_CHECKING
from uuid import UUID

from app.integrations.crm.crm_types import (
    CRMSystem,
    CRMCompanyPayload,
    CRMContactPayload,
    CRMDealPayload,
    CRMActivityPayload,
    CRMSyncResult,
)

if TYPE_CHECKING:
    from app.integrations.sync.crm_sync_service import CRMSyncService
    from app.integrations.credentials.crm_credentials_store import CRMCredentialsStore


logger = logging.getLogger(__name__)


class CRMSyncListener:
    """
    High-Level Listener für Sync-Events.

    Aufgaben:
      - Ermitteln, welche CRM-Systeme für einen Tenant verbunden sind
      - CRMSyncService für jedes System aufrufen
      - Ergebnisse pro CRM-System zurückgeben
    """

    def __init__(
        self,
        sync_service: "CRMSyncService",
        credentials_store: "CRMCredentialsStore",
    ) -> None:
        self._sync_service = sync_service
        self._credentials_store = credentials_store

    # ------------------------------------------------------------------
    # Internal helper
    # ------------------------------------------------------------------

    async def _get_connected_systems(self, tenant_id: UUID) -> list[CRMSystem]:
        """
        Liefert alle aktiv verbundenen CRM-Systeme für den Tenant.
        Erwartet, dass der CredentialsStore eine passende Methode bereitstellt.
        """
        systems = await self._credentials_store.list_connected_systems(tenant_id)
        logger.debug(
            "Connected CRM systems for tenant_id=%s: %s",
            tenant_id,
            [s.value for s in systems],
        )
        return list(systems)

    # ------------------------------------------------------------------
    # Company / Account Events
    # ------------------------------------------------------------------

    async def on_company_changed(
        self,
        tenant_id: UUID,
        payload: CRMCompanyPayload,
    ) -> Dict[CRMSystem, CRMSyncResult]:
        """
        Wird z.B. aufgerufen, wenn sich eine Company in LeadLane ändert.
        Synct zu allen verbundenen CRMs.
        """
        systems = await self._get_connected_systems(tenant_id)
        results: Dict[CRMSystem, CRMSyncResult] = {}

        if not systems:
            logger.info(
                "No connected CRMs for company sync: tenant_id=%s, leadlane_company_id=%s",
                tenant_id,
                payload.leadlane_company_id,
            )
            return results

        async def _sync(system: CRMSystem) -> tuple[CRMSystem, CRMSyncResult]:
            res = await self._sync_service.sync_company_to_crm(
                tenant_id=tenant_id,
                crm_system=system,
                payload=payload,
            )
            return system, res

        pairs = await asyncio.gather(*[_sync(s) for s in systems])
        results = {system: result for system, result in pairs}
        return results

    # ------------------------------------------------------------------
    # Contact Events
    # ------------------------------------------------------------------

    async def on_contact_changed(
        self,
        tenant_id: UUID,
        payload: CRMContactPayload,
    ) -> Dict[CRMSystem, CRMSyncResult]:
        systems = await self._get_connected_systems(tenant_id)
        results: Dict[CRMSystem, CRMSyncResult] = {}

        if not systems:
            logger.info(
                "No connected CRMs for contact sync: tenant_id=%s, leadlane_contact_id=%s",
                tenant_id,
                payload.leadlane_contact_id,
            )
            return results

        async def _sync(system: CRMSystem) -> tuple[CRMSystem, CRMSyncResult]:
            res = await self._sync_service.sync_contact_to_crm(
                tenant_id=tenant_id,
                crm_system=system,
                payload=payload,
            )
            return system, res

        pairs = await asyncio.gather(*[_sync(s) for s in systems])
        results = {system: result for system, result in pairs}
        return results

    # ------------------------------------------------------------------
    # Deal / Opportunity Events
    # ------------------------------------------------------------------

    async def on_deal_changed(
        self,
        tenant_id: UUID,
        payload: CRMDealPayload,
    ) -> Dict[CRMSystem, CRMSyncResult]:
        systems = await self._get_connected_systems(tenant_id)
        results: Dict[CRMSystem, CRMSyncResult] = {}

        if not systems:
            logger.info(
                "No connected CRMs for deal sync: tenant_id=%s, leadlane_opportunity_id=%s",
                tenant_id,
                payload.leadlane_opportunity_id,
            )
            return results

        async def _sync(system: CRMSystem) -> tuple[CRMSystem, CRMSyncResult]:
            # Dein Service heißt aktuell sync_opportunity_to_crm
            res = await self._sync_service.sync_opportunity_to_crm(
                tenant_id=tenant_id,
                crm_system=system,
                payload=payload,
            )
            return system, res

        pairs = await asyncio.gather(*[_sync(s) for s in systems])
        results = {system: result for system, result in pairs}
        return results

    # ------------------------------------------------------------------
    # Activity Events
    # ------------------------------------------------------------------

    async def on_activity_created(
        self,
        tenant_id: UUID,
        payload: CRMActivityPayload,
    ) -> Dict[CRMSystem, CRMSyncResult]:
        systems = await self._get_connected_systems(tenant_id)
        results: Dict[CRMSystem, CRMSyncResult] = {}

        if not systems:
            logger.info(
                "No connected CRMs for activity sync: tenant_id=%s, leadlane_activity_id=%s",
                tenant_id,
                payload.leadlane_activity_id,
            )
            return results

        async def _sync(system: CRMSystem) -> tuple[CRMSystem, CRMSyncResult]:
            res = await self._sync_service.sync_activity_to_crm(
                tenant_id=tenant_id,
                crm_system=system,
                payload=payload,
            )
            return system, res

        pairs = await asyncio.gather(*[_sync(s) for s in systems])
        results = {system: result for system, result in pairs}
        return results
