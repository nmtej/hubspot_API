# app/integrations/crm/hubspot/hubspot_auth.py
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Optional
from urllib.parse import urlencode

import httpx

from app.config import settings
from app.integrations.credentials.crm_credentials_store import CRMConnectionInfo
from app.integrations.crm.crm_types import CRMSystem

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Optional
from urllib.parse import urlencode

import httpx

from app.config import settings
from app.integrations.credentials.crm_credentials_store import CRMConnectionInfo
from app.integrations.crm.crm_types import CRMSystem


HUBSPOT_OAUTH_AUTHORIZE_URL = "https://app.hubspot.com/oauth/authorize"
HUBSPOT_OAUTH_TOKEN_URL = "https://api.hubapi.com/oauth/v1/token"


@dataclass
class HubSpotTokenResponse:
    access_token: str
    refresh_token: Optional[str]
    expires_in: Optional[int]
    token_type: Optional[str]
    scope: Optional[str]


# --- Compatibility shims for older code ------------------------------


class HubSpotAuthError(Exception):
    """
    Generic error during HubSpot OAuth / token handling.

    Newer code may not use this directly anymore, but older modules
    (hubspot_api, hubspot __init__) still import it.
    """
    pass


@dataclass
class HubSpotCredentials:
    """
    Backwards-compat wrapper around CRMConnectionInfo.

    Newer code uses CRMConnectionInfo directly. This class exists so that
    older code which passes a HubSpotCredentials instance into HubSpotAPI
    can still work.
    """
    connection_info: CRMConnectionInfo

    def is_expired(self, skew_seconds: int = 60) -> bool:
        # delegate to CRMConnectionInfo
        return self.connection_info.is_expired(skew_seconds=skew_seconds)

    def build_headers(self, extra: Optional[dict] = None) -> dict:
        # use the shared header builder in this module
        return HubSpotOAuthClient.build_headers(self.connection_info, extra=extra)


class HubSpotOAuthClient:
    """
    Verantwortlich für:
    - Build der Authorization URL
    - Code -> Token
    - Refresh Token
    - Konvertierung der Token-Response in CRMConnectionInfo
    """

    def __init__(self) -> None:
        self.client_id = settings.hubspot_client_id
        self.client_secret = settings.hubspot_client_secret
        self.redirect_uri = settings.hubspot_redirect_uri
        self.default_scopes = settings.hubspot_scopes

    def build_authorization_url(self, state: str) -> str:
        params = {
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "scope": self.default_scopes,
            "response_type": "code",
            "state": state,
        }
        return f"{HUBSPOT_OAUTH_AUTHORIZE_URL}?{urlencode(params)}"

    async def exchange_code_for_tokens(self, code: str) -> HubSpotTokenResponse:
        data = {
            "grant_type": "authorization_code",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "redirect_uri": self.redirect_uri,
            "code": code,
        }

        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(HUBSPOT_OAUTH_TOKEN_URL, data=data)

        resp.raise_for_status()
        payload = resp.json()

        return HubSpotTokenResponse(
            access_token=payload.get("access_token"),
            refresh_token=payload.get("refresh_token"),
            expires_in=payload.get("expires_in"),
            token_type=payload.get("token_type"),
            scope=payload.get("scope"),
        )

    async def refresh_access_token(self, refresh_token: str) -> HubSpotTokenResponse:
        data = {
            "grant_type": "refresh_token",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "refresh_token": refresh_token,
        }

        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(HUBSPOT_OAUTH_TOKEN_URL, data=data)

        resp.raise_for_status()
        payload = resp.json()

        return HubSpotTokenResponse(
            access_token=payload.get("access_token"),
            refresh_token=payload.get("refresh_token", refresh_token),
            expires_in=payload.get("expires_in"),
            token_type=payload.get("token_type"),
            scope=payload.get("scope"),
        )

    def token_response_to_connection_info(
        self,
        tenant_id,
        crm_system,
        token: HubSpotTokenResponse,
        actor: Optional[str] = None,
    ) -> CRMConnectionInfo:
        now = datetime.now(timezone.utc)
        expires_at = None
        if token.expires_in:
            expires_at = now + timedelta(seconds=token.expires_in)

        return CRMConnectionInfo(
            tenant_id=tenant_id,
            crm_system=crm_system if isinstance(crm_system, CRMSystem) else CRMSystem(crm_system),
            access_token=token.access_token,
            refresh_token=token.refresh_token,
            expires_at=expires_at,
            token_type=token.token_type,
            scope=token.scope,
            created_by=actor,
            modified_by=actor,
            created_time=now,
            last_modified_time=now,
            is_enabled=True,
        )

    @staticmethod
    def build_headers(info: CRMConnectionInfo, extra: Optional[dict] = None) -> dict:
        if not info.access_token:
            raise RuntimeError("No HubSpot access token.")

        headers = {
            "User-Agent": "LeadLane-CRM-Integration/1.0",
            "Accept": "application/json",
            "Authorization": f"Bearer {info.access_token}",
        }

        if extra:
            headers.update(extra)

        return headers
