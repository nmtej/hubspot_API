# app/integrations/crm/hubspot/hubspot_client.py
from __future__ import annotations

from typing import Any, Dict, Optional
from uuid import UUID

import httpx

from app.config import settings
from app.integrations.credentials.crm_credentials_store import (
    CRMCredentialsStore,
    CRMConnectionInfo,
)
from app.integrations.crm.crm_types import (
    CRMSystem,
    CRMCompanyPayload,
    CRMContactPayload,
    CRMDealPayload,
    CRMActivityPayload,
    CRMSyncResult,
    CRMSyncError,
)
from app.integrations.crm.hubspot.hubspot_refresh import refresh_hubspot_connection
from app.integrations.mapping import CRMFieldMappingEngine



class HubSpotClientError(RuntimeError):
    pass


class HubSpotClient:
    """
    HubSpot-Client pro Tenant.

    - Holt bei jedem Request via CRMCredentialsStore.get_active_credentials(...)
      ein (ggf. refreshed) Access-Token.
    - Bietet High-Level-Methoden, die direkt CRMSyncResult liefern.
    """

    def __init__(
        self,
        tenant_id: UUID,
        credentials_store: CRMCredentialsStore,
        mapping_engine: CRMFieldMappingEngine,
        base_url: Optional[str] = None,
    ) -> None:
        self._tenant_id = tenant_id
        self._credentials_store = credentials_store
        self._mapping_engine = mapping_engine
        self.base_url = (base_url or settings.hubspot_base_url)
  
    # ------------------------------------------------------------------
    # Intern: Credentials + Header
    # ------------------------------------------------------------------

    async def _get_connection(self) -> CRMConnectionInfo:
        return await self._credentials_store.get_active_credentials(
            tenant_id=self._tenant_id,
            crm_system=CRMSystem.HUBSPOT,
            refresh_fn=refresh_hubspot_connection,
        )

    async def _build_headers(self) -> Dict[str, str]:
        info = await self._get_connection()
        if not info.access_token:
            raise HubSpotClientError("No HubSpot access token available.")

        return {
            "User-Agent": "LeadLane-CRM-Integration/1.0",
            "Accept": "application/json",
            "Authorization": f"Bearer {info.access_token}",
        }

    # ------------------------------------------------------------------
    # Generischer Request
    # ------------------------------------------------------------------

    async def _request(
        self,
        method: str,
        path: str,
        *,
        params: Optional[Dict[str, Any]] = None,
        json_body: Optional[Any] = None,
        timeout: float = 10.0,
    ) -> httpx.Response:
        url = f"{self.base_url.rstrip('/')}/{path.lstrip('/')}"
        headers = await self._build_headers()

        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.request(
                method=method.upper(),
                url=url,
                headers=headers,
                params=params,
                json=json_body,
            )
        return resp

    async def _post_json(
        self,
        path: str,
        *,
        json_body: Any,
        timeout: float = 10.0,
    ) -> Dict[str, Any]:
        resp = await self._request("POST", path, json_body=json_body, timeout=timeout)
        resp.raise_for_status()
        return resp.json()

    # ------------------------------------------------------------------
    # High-Level-Methoden
    # ------------------------------------------------------------------

    def _handle_http_error(
        self,
        exc: httpx.HTTPStatusError,
        *,
        crm_object_type: str,
        leadlane_id: Optional[str],
    ) -> CRMSyncResult:
        resp = exc.response
        status = resp.status_code
        try:
            payload_json = resp.json()
        except Exception:
            payload_json = {"body": resp.text}

        if status in (401, 403):
            code = "hubspot_auth_error"
            message = f"HubSpot {crm_object_type} request failed due to invalid or missing credentials."
        elif status == 404:
            code = "hubspot_not_found"
            message = f"HubSpot {crm_object_type} not found."
        elif status == 429:
            code = "hubspot_rate_limited"
            message = f"HubSpot rate limit exceeded for {crm_object_type}."
        elif 400 <= status < 500:
            code = "hubspot_validation_error"
            message = f"HubSpot rejected the {crm_object_type} payload."
        else:
            code = "hubspot_server_error"
            message = f"HubSpot {crm_object_type} request failed with server error."

        error = CRMSyncError(
            code=code,
            message=message,
            details={
                "status_code": status,
                "body": payload_json,
            },
        )

        return CRMSyncResult(
            success=False,
            crm_system=CRMSystem.HUBSPOT,
            crm_object_type=crm_object_type,
            crm_id=None,
            leadlane_id=leadlane_id,
            errors=[error],
            raw_response=payload_json,
        )

        async def upsert_company(
            self,
            payload: CRMCompanyPayload,
            existing_crm_id: Optional[str] = None,
        ) -> CRMSyncResult:
            leadlane_id = payload.leadlane_sub_company_id or payload.central_sub_company_id

            # NEU: Properties via Mapping Engine bauen
            properties = await self._mapping_engine.map_udm_to_crm_properties(
                tenant_id=self._tenant_id,
                crm_system=CRMSystem.HUBSPOT,
                object_type="company",
                udm_object=payload,
                extra_fields=payload.properties,
            )
            body = {"properties": properties}

            try:
                if existing_crm_id:
                    path = f"/crm/v3/objects/companies/{existing_crm_id}"
                    resp = await self._request("PATCH", path, json_body=body)
                    resp.raise_for_status()
                    payload_json = resp.json()
                    crm_id = existing_crm_id
                else:
                    payload_json = await self._post_json(
                        "/crm/v3/objects/companies",
                        json_body=body,
                    )
                    crm_id = str(payload_json.get("id")) if payload_json.get("id") else None

                return CRMSyncResult(
                    success=True,
                    crm_system=CRMSystem.HUBSPOT,
                    crm_object_type="company",
                    crm_id=crm_id,
                    leadlane_id=leadlane_id,
                    errors=[],
                    raw_response=payload_json,
                )

            except httpx.HTTPStatusError as exc:
                return self._handle_http_error(
                    exc,
                    crm_object_type="company",
                    leadlane_id=leadlane_id,
                )


        async def upsert_contact(
            self,
            payload: CRMContactPayload,
            existing_crm_id: Optional[str] = None,
        ) -> CRMSyncResult:
            leadlane_id = payload.leadlane_contact_id

            properties = await self._mapping_engine.map_udm_to_crm_properties(
                tenant_id=self._tenant_id,
                crm_system=CRMSystem.HUBSPOT,
                object_type="contact",
                udm_object=payload,
                extra_fields=payload.properties,
            )
            body = {"properties": properties}

            try:
                if existing_crm_id:
                    path = f"/crm/v3/objects/contacts/{existing_crm_id}"
                    resp = await self._request("PATCH", path, json_body=body)
                    resp.raise_for_status()
                    payload_json = resp.json()
                    crm_id = existing_crm_id
                else:
                    payload_json = await self._post_json(
                        "/crm/v3/objects/contacts",
                        json_body=body,
                    )
                    crm_id = str(payload_json.get("id")) if payload_json.get("id") else None

                return CRMSyncResult(
                    success=True,
                    crm_system=CRMSystem.HUBSPOT,
                    crm_object_type="contact",
                    crm_id=crm_id,
                    leadlane_id=leadlane_id,
                    errors=[],
                    raw_response=payload_json,
                )

            except httpx.HTTPStatusError as exc:
                return self._handle_http_error(
                    exc,
                    crm_object_type="contact",
                    leadlane_id=leadlane_id,
                )

                
        async def upsert_deal(
            self,
            payload: CRMDealPayload,
            existing_crm_id: Optional[str] = None,
        ) -> CRMSyncResult:
            leadlane_id = payload.leadlane_demo_id or payload.leadlane_account_id

            properties = await self._mapping_engine.map_udm_to_crm_properties(
                tenant_id=self._tenant_id,
                crm_system=CRMSystem.HUBSPOT,
                object_type="deal",
                udm_object=payload,
                extra_fields=payload.properties,
            )
            body = {"properties": properties}

            try:
                if existing_crm_id:
                    path = f"/crm/v3/objects/deals/{existing_crm_id}"
                    resp = await self._request("PATCH", path, json_body=body)
                    resp.raise_for_status()
                    payload_json = resp.json()
                    crm_id = existing_crm_id
                else:
                    payload_json = await self._post_json(
                        "/crm/v3/objects/deals",
                        json_body=body,
                    )
                    crm_id = str(payload_json.get("id")) if payload_json.get("id") else None

                return CRMSyncResult(
                    success=True,
                    crm_system=CRMSystem.HUBSPOT,
                    crm_object_type="deal",
                    crm_id=crm_id,
                    leadlane_id=leadlane_id,
                    errors=[],
                    raw_response=payload_json,
                )

            except httpx.HTTPStatusError as exc:
                return self._handle_http_error(
                    exc,
                    crm_object_type="deal",
                    leadlane_id=leadlane_id,
                )



    async def create_activity(self, payload: CRMActivityPayload) -> CRMSyncResult:
        leadlane_id = (
            payload.leadlane_demo_id
            or payload.leadlane_contact_id
            or payload.leadlane_sub_company_id
        )

        # Platzhalter-Mapping – hier kannst du später auf echte HubSpot-Engagements mappen
        body = {
            "properties": {
                "hs_timestamp": payload.timestamp,
                "hs_note_body": payload.body,
            }
        }

        try:
            data = await self._post_json("/crm/v3/objects/notes", json_body=body)
            crm_id = str(data.get("id")) if data.get("id") else None
            return CRMSyncResult(
                success=True,
                crm_system=CRMSystem.HUBSPOT,
                crm_object_type="activity",
                crm_id=crm_id,
                leadlane_id=leadlane_id,
                errors=[],
                raw_response=data,
            )
        except httpx.HTTPStatusError as exc:
            resp = exc.response
            try:
                payload_json = resp.json()
            except Exception:
                payload_json = {"body": resp.text}

            error = CRMSyncError(
                code="hubspot_http_error",
                message="HubSpot activity creation failed.",
                details={
                    "status_code": resp.status_code,
                    "body": payload_json,
                },
            )
            return CRMSyncResult(
                success=False,
                crm_system=CRMSystem.HUBSPOT,
                crm_object_type="activity",
                crm_id=None,
                leadlane_id=leadlane_id,
                errors=[error],
                raw_response=payload_json,
            )
