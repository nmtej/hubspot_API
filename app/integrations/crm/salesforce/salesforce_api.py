# app/integrations/crm/salesforce/salesforce_api.py
from __future__ import annotations

from typing import Any, Dict, Optional, Mapping

import httpx

from .salesforce_auth import SalesforceCredentials, SalesforceAuthError


class SalesforceAPIError(RuntimeError):
    """
    Fehler bei der Kommunikation mit der Salesforce REST API.
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


class SalesforceAPI:
    """
    Dünner Wrapper um die Salesforce REST API.

    Base-URL wird aus instance_url + services/data/vXX.0 gebaut.
    Diese Klasse kennt KEINE LeadLane-spezifischen Payloads.
    """

    def __init__(
        self,
        credentials: SalesforceCredentials,
        api_version: str = "v59.0",  # Version bei Bedarf anpassbar
        timeout: float = 10.0,
        client: Optional[httpx.AsyncClient] = None,
    ) -> None:
        if not credentials.instance_url:
            raise SalesforceAuthError("Salesforce instance_url ist nicht gesetzt.")

        self._credentials = credentials
        self._api_version = api_version
        self._timeout = timeout

        base = credentials.instance_url.rstrip("/")
        self._base_url = f"{base}/services/data/{self._api_version}"

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
        Interner Helper für HTTP-Requests gegen Salesforce.
        """
        if self._credentials.is_expired():
            # Später könnte hier ein Refresh-Flow implementiert werden.
            raise SalesforceAuthError("Salesforce access_token ist abgelaufen.")

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
            raise SalesforceAPIError(
                f"HTTP-Fehler bei Request an Salesforce: {exc!r}"
            ) from exc

        if response.status_code >= 400:
            try:
                body = response.json()
            except ValueError:
                body = response.text

            raise SalesforceAPIError(
                message=f"Salesforce antwortet mit Status {response.status_code}",
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
    # High-Level Convenience-Methoden (Accounts, Contacts, Opportunities)
    # ----------------------------------------------------------

    async def upsert_account(
        self,
        data: Mapping[str, Any],
        sf_account_id: Optional[str] = None,
    ) -> Any:
        """
        Vereinfachter Upsert für Accounts.

        - POST /sobjects/Account
        - PATCH /sobjects/Account/{Id}
        """
        path = "sobjects/Account" + (f"/{sf_account_id}" if sf_account_id else "")
        method = "PATCH" if sf_account_id else "POST"
        return await self._request(method, path, json=data)

    async def upsert_contact(
        self,
        data: Mapping[str, Any],
        sf_contact_id: Optional[str] = None,
    ) -> Any:
        """
        Vereinfachter Upsert für Contacts.
        """
        path = "sobjects/Contact" + (f"/{sf_contact_id}" if sf_contact_id else "")
        method = "PATCH" if sf_contact_id else "POST"
        return await self._request(method, path, json=data)

    async def upsert_opportunity(
        self,
        data: Mapping[str, Any],
        sf_opportunity_id: Optional[str] = None,
    ) -> Any:
        """
        Vereinfachter Upsert für Opportunities.
        """
        path = "sobjects/Opportunity" + (f"/{sf_opportunity_id}" if sf_opportunity_id else "")
        method = "PATCH" if sf_opportunity_id else "POST"
        return await self._request(method, path, json=data)

    async def get_opportunity(self, sf_opportunity_id: str) -> Any:
        """
        Holt eine Opportunity aus Salesforce.
        """
        path = f"sobjects/Opportunity/{sf_opportunity_id}"
        return await self._request("GET", path)
