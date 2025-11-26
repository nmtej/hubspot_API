# app/integrations/crm/crm_client.py
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional, List
from uuid import UUID

from .crm_types import (
    CRMSystem,
    CRMCompanyPayload,
    CRMContactPayload,
    CRMDealPayload,
    CRMActivityPayload,
    CRMSyncResult,
)


class CRMClient(ABC):
    """
    Abstraktes Interface für alle CRM-Clients (HubSpot, Salesforce, Pipedrive, SAP B1).

    WICHTIG:
    - Arbeitet nur mit generischen CRM*Payloads.
    - Kennt eure UDM-Klassen (Company, Contact, Opportunity) NICHT.
      Das passiert eine Ebene darüber im Mapping/Sync-Service.
    """

    def __init__(self, tenant_id: UUID) -> None:
        self._tenant_id = tenant_id

    @property
    @abstractmethod
    def system(self) -> CRMSystem:
        """
        Welches CRM-System dieser Client repräsentiert.
        """
        raise NotImplementedError

    # -------------------------------------------------------------------------
    # Auth / Connectivity
    # -------------------------------------------------------------------------

    @abstractmethod
    async def check_auth(self) -> bool:
        """
        Prüft, ob die aktuellen Credentials gültig sind (z.B. Test-API-Call).
        """
        raise NotImplementedError

    @abstractmethod
    async def refresh_auth(self) -> bool:
        """
        Versucht, die Auth-Credentials zu refreshen (z.B. via Refresh Token).
        Gibt True zurück, wenn erfolgreich.
        """
        raise NotImplementedError

    # -------------------------------------------------------------------------
    # Company / Account
    # -------------------------------------------------------------------------

    @abstractmethod
    async def upsert_company(self, payload: CRMCompanyPayload) -> CRMSyncResult:
        """
        Erstellt oder aktualisiert eine Company/Account im CRM.
        """
        raise NotImplementedError

    # -------------------------------------------------------------------------
    # Contact
    # -------------------------------------------------------------------------

    @abstractmethod
    async def upsert_contact(self, payload: CRMContactPayload) -> CRMSyncResult:
        """
        Erstellt oder aktualisiert einen Contact im CRM.
        """
        raise NotImplementedError

    # -------------------------------------------------------------------------
    # Deal / Opportunity
    # -------------------------------------------------------------------------

    @abstractmethod
    async def upsert_deal(self, payload: CRMDealPayload) -> CRMSyncResult:
        """
        Erstellt oder aktualisiert einen Deal/Opportunity im CRM.
        """
        raise NotImplementedError

    @abstractmethod
    async def get_deal(
        self,
        crm_deal_id: str,
    ) -> Optional[CRMDealPayload]:
        """
        Holt einen Deal/Opportunity aus dem CRM (z.B. für Status-Sync zurück zu LeadLane).
        """
        raise NotImplementedError

    # -------------------------------------------------------------------------
    # Activities
    # -------------------------------------------------------------------------

    @abstractmethod
    async def create_activity(self, payload: CRMActivityPayload) -> CRMSyncResult:
        """
        Erstellt eine Activity (Call, E-Mail, Meeting, Task, Note) im CRM.
        """
        raise NotImplementedError

    # -------------------------------------------------------------------------
    # Helper / Bulk
    # -------------------------------------------------------------------------

    async def upsert_companies_bulk(
        self,
        payloads: List[CRMCompanyPayload],
    ) -> List[CRMSyncResult]:
        """
        Default-Implementierung über Einzel-Calls.
        Konkrete Clients können das mit echten Bulk-APIs überschreiben.
        """
        results: List[CRMSyncResult] = []
        for p in payloads:
            results.append(await self.upsert_company(p))
        return results

    async def upsert_contacts_bulk(
        self,
        payloads: List[CRMContactPayload],
    ) -> List[CRMSyncResult]:
        results: List[CRMSyncResult] = []
        for p in payloads:
            results.append(await self.upsert_contact(p))
        return results

    async def upsert_deals_bulk(
        self,
        payloads: List[CRMDealPayload],
    ) -> List[CRMSyncResult]:
        results: List[CRMSyncResult] = []
        for p in payloads:
            results.append(await self.upsert_deal(p))
        return results
