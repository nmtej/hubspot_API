# app/integrations/crm/sap_b1/sap_b1_client.py
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
from .sap_b1_auth import SAPB1Credentials
from .sap_b1_api import SAPB1API


class SAPB1CRMClient(CRMClient):
    """
    Konkrete CRMClient-Implementierung für SAP Business One.

    Aktuell mit Stubs, die einheitliche CRMSyncResult-Objekte liefern.
    Später:
      - Mapping UDM → SAP B1 BusinessPartners/ContactEmployees/SalesOpportunities
      - Nutzung von SAPB1API für echte Upserts.
    """

    def __init__(self, tenant_id: UUID, credentials: Mapping[str, Any]) -> None:
        super().__init__(tenant_id)

        self._credentials_raw: Dict[str, Any] = dict(credentials)
        self._credentials = SAPB1Credentials.from_mapping(credentials)

        # API-Client (aktuell ungenutzt, aber vorbereitet)
        self._api = SAPB1API(self._credentials)

    # ------------------------------------------------------------------
    # CRMClient Interface
    # ------------------------------------------------------------------

    @property
    def system(self) -> CRMSystem:
        return CRMSystem.SAP_B1

    async def check_auth(self) -> bool:
        """
        Minimal-Check: base_url, company_db, session_id vorhanden.
        """
        return bool(
            self._credentials.base_url
            and self._credentials.company_db
            and self._credentials.session_id
        )

    async def refresh_auth(self) -> bool:
        """
        Placeholder für (Re-)Login gegen die SAP B1 Service Layer API.

        TODO:
        - username/password + company_db nutzen, um /Login aufzurufen
        - session_id + expires_at aktualisieren
        """
        return False

    # ------------------------------------------------------------------
    # Company / Business Partner
    # ------------------------------------------------------------------

    async def upsert_company(self, payload: CRMCompanyPayload) -> CRMSyncResult:
        leadlane_id = (
            payload.leadlane_sub_company_id
            or payload.central_sub_company_id
        )

        return self._not_implemented_result(
            crm_object_type="business_partner",
            leadlane_id=leadlane_id,
            code="sap_b1_upsert_company_not_implemented",
            message="upsert_company für SAP B1 ist noch nicht implementiert.",
        )

    # ------------------------------------------------------------------
    # Contact
    # ------------------------------------------------------------------

    async def upsert_contact(self, payload: CRMContactPayload) -> CRMSyncResult:
        return self._not_implemented_result(
            crm_object_type="contact_employee",
            leadlane_id=payload.leadlane_contact_id,
            code="sap_b1_upsert_contact_not_implemented",
            message="upsert_contact für SAP B1 ist noch nicht implementiert.",
        )

    # ------------------------------------------------------------------
    # Deal / Opportunity
    # ------------------------------------------------------------------

    async def upsert_deal(self, payload: CRMDealPayload) -> CRMSyncResult:
        leadlane_id = payload.leadlane_demo_id or payload.leadlane_account_id

        return self._not_implemented_result(
            crm_object_type="sales_opportunity",
            leadlane_id=leadlane_id,
            code="sap_b1_upsert_deal_not_implemented",
            message="upsert_deal für SAP B1 ist noch nicht implementiert.",
        )

    async def get_deal(self, crm_deal_id: str) -> Optional[CRMDealPayload]:
        """
        Holt eine SalesOpportunity aus SAP B1.
        Solange kein Mapping B1 → CRMDealPayload definiert ist, geben wir None zurück.
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
            code="sap_b1_create_activity_not_implemented",
            message="create_activity für SAP B1 ist noch nicht implementiert.",
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


def _sap_b1_factory(config: CRMClientConfig) -> CRMClient:
    return SAPB1CRMClient(
        tenant_id=config.tenant_id,
        credentials=config.credentials,
    )


register_crm_client(CRMSystem.SAP_B1, _sap_b1_factory)
