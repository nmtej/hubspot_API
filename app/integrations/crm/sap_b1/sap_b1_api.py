# app/integrations/crm/sap_b1/sap_b1_api.py
from __future__ import annotations

from typing import Any, Dict, Optional, Mapping

import httpx

from .sap_b1_auth import SAPB1Credentials, SAPB1AuthError


class SAPB1APIError(RuntimeError):
    """
    Fehler bei der Kommunikation mit der SAP Business One Service Layer API.
    """

    def __init__(
        self,
        message: str,
        status_code: Optional[int] = None,
        response_body: Optional[Any] = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.response_body = response_body


class SAPB1API:
    """
    Dünner Wrapper um die SAP B1 Service Layer API (OData / REST).

    Base-URL wird aus base_url + /b1s/v1 gebaut.
    Diese Klasse kennt KEINE LeadLane-spezifischen Payloads.
    """

    def __init__(
        self,
        credentials: SAPB1Credentials,
        timeout: float = 10.0,
        client: Optional[httpx.AsyncClient] = None,
    ) -> None:
        if not credentials.base_url:
            raise SAPB1AuthError("SAP B1 base_url ist nicht gesetzt.")

        self._credentials = credentials
        self._timeout = timeout

        base = credentials.base_url.rstrip("/")
        self._base_url = f"{base}/b1s/v1"

        self._owns_client = client is None
        self._client: httpx.AsyncClient = client or httpx.AsyncClient(
            timeout=self._timeout,
        )

    async def close(self) -> None:
        if self._owns_client:
            await self._client.aclose()

    # ----------------------------------------------------------
    # Low-Level Request Helper
    # ----------------------------------------------------------

    async def _request(
        self,
        method: str,
        path: str,
        *,
        params: Optional[Mapping[str, Any]] = None,
        json: Optional[Any] = None,
    ) -> Any:
        """
        Interner Helper für HTTP-Requests gegen die SAP B1 Service Layer API.
        """
        if self._credentials.is_expired():
            # Später könnte hier ein automatischer Re-Login stattfinden.
            raise SAPB1AuthError("SAP B1 Session ist abgelaufen.")

        url = f"{self._base_url}/{path.lstrip('/')}"
        headers = self._credentials.build_headers()

        try:
            response = await self._client.request(
                method=method,
                url=url,
                headers=headers,
                params=params,
                json=json,
            )
        except httpx.HTTPError as exc:
            raise SAPB1APIError(
                f"HTTP-Fehler bei Request an SAP B1: {exc!r}"
            ) from exc

        if response.status_code >= 400:
            try:
                body = response.json()
            except ValueError:
                body = response.text

            raise SAPB1APIError(
                message=f"SAP B1 antwortet mit Status {response.status_code}",
                status_code=response.status_code,
                response_body=body,
            )

        if response.content:
            try:
                return response.json()
            except ValueError:
                return response.text

        return None

    # ----------------------------------------------------------
    # High-Level Convenience-Methoden
    # (BusinessPartner, ContactEmployee, SalesOpportunities)
    # ----------------------------------------------------------

    async def upsert_business_partner(
        self,
        data: Mapping[str, Any],
        bp_code: Optional[str] = None,
    ) -> Any:
        """
        Vereinfachter Upsert für BusinessPartner.

        In der Service Layer API wären die Pfade typischerweise:
          POST   /BusinessPartners
          PATCH  /BusinessPartners('<CardCode>')
        """
        if bp_code:
            path = f"BusinessPartners('{bp_code}')"
            method = "PATCH"
        else:
            path = "BusinessPartners"
            method = "POST"

        return await self._request(method, path, json=data)

    async def upsert_contact_person(
        self,
        data: Mapping[str, Any],
        contact_code: Optional[int] = None,
    ) -> Any:
        """
        Vereinfachter Upsert für ContactEmployees.
        Je nach Setup braucht man hier u.U. andere Schlüssel.
        """
        if contact_code is not None:
            path = f"ContactEmployees({contact_code})"
            method = "PATCH"
        else:
            path = "ContactEmployees"
            method = "POST"

        return await self._request(method, path, json=data)

    async def upsert_opportunity(
        self,
        data: Mapping[str, Any],
        op_id: Optional[int] = None,
    ) -> Any:
        """
        Vereinfachter Upsert für SalesOpportunities.
        """
        if op_id is not None:
            path = f"SalesOpportunities({op_id})"
            method = "PATCH"
        else:
            path = "SalesOpportunities"
            method = "POST"

        return await self._request(method, path, json=data)

    async def get_opportunity(self, op_id: int) -> Any:
        """
        Holt eine SalesOpportunity.
        """
        path = f"SalesOpportunities({op_id})"
        return await self._request("GET", path)
