# app/integrations/crm/salesforce/salesforce_client.py
from __future__ import annotations

from typing import Any, Mapping, Optional, Dict
from uuid import UUID

from ..crm_client import CRMClient
from ..crm_types import (
    CRMSystem,
    CRMCompanyPayload,
    CRMContactPayload,
    CRMDealPayload,
    CRMActivityPayload,
    CRMSyncResult,
    CRMSyncError,
)
from ..crm_client_factory import (
    CRMClientConfig,
    register_crm_client,
)
from .salesforce_auth import SalesforceCredentials
from .salesforce_api import SalesforceAPI


class SalesforceCRMClient(CRMClient):
    """
    Konkrete CRMClient-Implementierung für Salesforce.

    Aktuell mit Stubs, die einheitliche CRMSyncResult-Objekte
    zurückgeben. Später kann hier SalesforceAPI + Mapping eingebaut werden.
    """

    def __init__(self, tenant_id: UUID, credentials: Mapping[str, Any]) -> None:
        super().__init__(tenant_id)

        self._credentials_raw: Dict[str, Any] = dict(credentials)
        self._credentials = SalesforceCredentials.from_mapping(credentials)

        # API-Client (aktuell ungenutzt, aber vorbereitet)
        self._api = SalesforceAPI(self._credentials)

    # ------------------------------------------------------------------
    # CRMClient Interface
    # ------------------------------------------------------------------

    @property
    def system(self) -> CRMSystem:
        return CRMSystem.SALESFORCE

    async def check_auth(self) -> bool:
        """
        Minimal-Check: access_token + instance_url vorhanden
        (ohne echten Test-Request).
        """
        return bool(self._credentials.access_token and self._credentials.instance_url)

    async def refresh_auth(self) -> bool:
        """
        Placeholder für OAuth-Refresh-Flow gegen Salesforce.

        TODO:
        - refresh_token nutzen, um neues access_token zu holen
        - Credentials aktualisieren
        """
        return False

    # ------------------------------------------------------------------
    # Company / Account
    # ------------------------------------------------------------------

    async def upsert_company(self, payload: CRMCompanyPayload) -> CRMSyncResult:
        """
        Erstellt/aktualisiert einen Account in Salesforce.
        Derzeit nur Not-Implemented-Result.
        """
        leadlane_id = (
            payload.leadlane_sub_company_id
            or payload.central_sub_company_id
        )

        return self._not_implemented_result(
            crm_object_type="account",
            leadlane_id=leadlane_id,
            code="salesforce_upsert_company_not_implemented",
            message="upsert_company für Salesforce ist noch nicht implementiert.",
        )

    # ------------------------------------------------------------------
    # Contact
    # ------------------------------------------------------------------

    async def upsert_contact(self, payload: CRMContactPayload) -> CRMSyncResult:
        return self._not_implemented_result(
            crm_object_type="contact",
            leadlane_id=payload.leadlane_contact_id,
            code="salesforce_upsert_contact_not_implemented",
            message="upsert_contact für Salesforce ist noch nicht implementiert.",
        )

    # ------------------------------------------------------------------
    # Deal / Opportunity
    # ------------------------------------------------------------------

    async def upsert_deal(self, payload: CRMDealPayload) -> CRMSyncResult:
        leadlane_id = payload.leadlane_demo_id or payload.leadlane_account_id

        return self._not_implemented_result(
            crm_object_type="opportunity",
            leadlane_id=leadlane_id,
            code="salesforce_upsert_deal_not_implemented",
            message="upsert_deal für Salesforce ist noch nicht implementiert.",
        )

    async def get_deal(self, crm_deal_id: str) -> Optional[CRMDealPayload]:
        """
        Holt eine Opportunity aus Salesforce.
        Solange kein Mapping SF → CRMDealPayload definiert ist, geben wir None zurück.
        """
        return None

    # ------------------------------------------------------------------
    # Activities
    # ------------------------------------------------------------------

    async def create_activity(
        self,
        payload: CRMActivityPayload,
    ) -> CRMSyncResult:
        return self._not_implemented_result(
            crm_object_type="activity",
            leadlane_id=(
                payload.leadlane_demo_id
                or payload.leadlane_contact_id
                or payload.leadlane_sub_company_id
            ),
            code="salesforce_create_activity_not_implemented",
            message="create_activity für Salesforce ist noch nicht implementiert.",
        )

    # ------------------------------------------------------------------
    # Helper
    # ------------------------------------------------------------------

    def _not_implemented_result(
        self,
        crm_object_type: str,
        leadlane_id: Optional[str],
        code: str,
        message: str,
    ) -> CRMSyncResult:
        return CRMSyncResult(
            success=False,
            crm_system=self.system,
            crm_object_type=crm_object_type,
            crm_id=None,
            leadlane_id=leadlane_id,
            errors=[
                CRMSyncError(
                    code=code,
                    message=message,
                    details={
                        "tenant_id": str(self._tenant_id),
                    },
                )
            ],
            raw_response=None,
        )


# ----------------------------------------------------------------------
# Registrierung in der CRM-Factory
# ----------------------------------------------------------------------


def _salesforce_factory(config: CRMClientConfig) -> CRMClient:
    return SalesforceCRMClient(
        tenant_id=config.tenant_id,
        credentials=config.credentials,
    )


register_crm_client(CRMSystem.SALESFORCE, _salesforce_factory)
