# app/integrations/crm/hubspot/hubspot_api.py
from __future__ import annotations

from typing import Any, Dict, Optional, Mapping

import httpx

from .hubspot_auth import HubSpotCredentials, HubSpotAuthError


class HubSpotAPIError(RuntimeError):
    """
    Fehler bei der Kommunikation mit der HubSpot-API.
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


class HubSpotAPI:
    """
    Dünne Wrapper-Klasse um die HubSpot REST API (v3).

    Diese Klasse kennt KEINE LeadLane-spezifischen Payloads, sondern
    arbeitet auf Dict-/JSON-Ebene. Mapping macht der HubSpotCRMClient.
    """

    def __init__(
        self,
        credentials: HubSpotCredentials,
        base_url: str = "https://api.hubapi.com",
        timeout: float = 10.0,
        client: Optional[httpx.AsyncClient] = None,
    ) -> None:
        self._credentials = credentials
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout
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
        Interner Helper für HTTP-Requests gegen HubSpot.

        - Fügt Base-URL hinzu
        - Setzt Auth-Header über HubSpotCredentials
        - Hebt Fehler in eine eigene Exception hoch
        """
        if self._credentials.is_expired():
            # Hier könnte später ein Refresh-Flow ausgelöst werden.
            # Für jetzt: konservativ Fehler werfen.
            raise HubSpotAuthError("HubSpot Access Token ist abgelaufen.")

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
            raise HubSpotAPIError(
                f"HTTP-Fehler bei Request an HubSpot: {exc!r}"
            ) from exc

        if response.status_code >= 400:
            try:
                body = response.json()
            except ValueError:
                body = response.text

            raise HubSpotAPIError(
                message=f"HubSpot antwortet mit Status {response.status_code}",
                status_code=response.status_code,
                response_body=body,
            )

        # Erfolgreicher Fall
        if response.content:
            try:
                return response.json()
            except ValueError:
                return response.text

        return None

    # ----------------------------------------------------------
    # High-Level Convenience-Methoden
    # (können später erweitert / spezialisiert werden)
    # ----------------------------------------------------------

    async def upsert_company(
        self,
        properties: Mapping[str, Any],
        hubspot_company_id: Optional[str] = None,
    ) -> Any:
        """
        Erstellt oder aktualisiert eine Company in HubSpot.

        Grobe Abbildung auf:
          POST /crm/v3/objects/companies
          PATCH /crm/v3/objects/companies/{companyId}
        """
        payload = {"properties": dict(properties)}

        if hubspot_company_id:
            path = f"/crm/v3/objects/companies/{hubspot_company_id}"
            return await self._request("PATCH", path, json=payload)

        path = "/crm/v3/objects/companies"
        return await self._request("POST", path, json=payload)

    async def upsert_contact(
        self,
        properties: Mapping[str, Any],
        hubspot_contact_id: Optional[str] = None,
    ) -> Any:
        """
        Vereinfachter Upsert für Contacts.

        In der Realität muss man hier evtl. deduplizieren (email, etc.).
        """
        payload = {"properties": dict(properties)}

        if hubspot_contact_id:
            path = f"/crm/v3/objects/contacts/{hubspot_contact_id}"
            return await self._request("PATCH", path, json=payload)

        path = "/crm/v3/objects/contacts"
        return await self._request("POST", path, json=payload)

    async def upsert_deal(
        self,
        properties: Mapping[str, Any],
        hubspot_deal_id: Optional[str] = None,
        associations: Optional[Dict[str, Any]] = None,
    ) -> Any:
        """
        Upsert für Deals (Opportunities).

        associations kann z.B. companies/contacts enthalten.
        """
        payload: Dict[str, Any] = {"properties": dict(properties)}
        if associations:
            payload["associations"] = associations

        if hubspot_deal_id:
            path = f"/crm/v3/objects/deals/{hubspot_deal_id}"
            return await self._request("PATCH", path, json=payload)

        path = "/crm/v3/objects/deals"
        return await self._request("POST", path, json=payload)

    async def get_deal(self, hubspot_deal_id: str) -> Any:
        """
        Holt einen Deal aus HubSpot.
        """
        path = f"/crm/v3/objects/deals/{hubspot_deal_id}"
        params = {"properties": ["dealname", "amount", "pipeline", "dealstage"]}
        return await self._request("GET", path, params=params)

    # Weitere Methoden (Activities, Engagements, Calls, Meetings, ...) können
    # später hier ergänzt werden.
