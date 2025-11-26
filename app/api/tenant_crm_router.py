# app/api/tenant_crm_router.py
from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID
import base64
import hashlib
import hmac
import json

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from app.config import settings
from app.integrations.credentials.crm_credentials_store import CRMCredentialsStore
from app.integrations.crm.crm_types import CRMSystem
from app.integrations.crm.hubspot.hubspot_auth import HubSpotOAuthClient

from app.dependencies import (
    ensure_path_tenant_matches_token,
    get_crm_credentials_store,
)
from app.security.auth import TokenData, get_current_token


tenant_crm_router = APIRouter(
    prefix="/tenants",
    tags=["tenant-crm"],
)

hubspot_oauth_client = HubSpotOAuthClient()


# ---------------------------------------------------------------------------
# OAuth State Helpers (signierter State für HubSpot-Connect)
# ---------------------------------------------------------------------------

def _get_hubspot_state_secret() -> str:
    secret = settings.hubspot_client_secret
    if not secret:
        raise RuntimeError("hubspot_client_secret is not configured")
    return secret


def _encode_oauth_state(tenant_id: UUID) -> str:
    payload = {"tenant_id": str(tenant_id)}
    body = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")

    secret = _get_hubspot_state_secret()
    mac = hmac.new(
        secret.encode("utf-8"),
        msg=body,
        digestmod=hashlib.sha256,
    )
    token_bytes = body + b"." + mac.digest()
    return base64.urlsafe_b64encode(token_bytes).decode("ascii").rstrip("=")


def _decode_and_verify_oauth_state(raw_state: str) -> UUID:
    if not raw_state:
        raise HTTPException(status_code=400, detail="Missing OAuth state")

    padded = raw_state + "=" * (-len(raw_state) % 4)
    try:
        data = base64.urlsafe_b64decode(padded.encode("ascii"))
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid state format")

    try:
        body, sig = data.rsplit(b".", 1)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid state format")

    secret = _get_hubspot_state_secret()
    mac = hmac.new(
        secret.encode("utf-8"),
        msg=body,
        digestmod=hashlib.sha256,
    )
    if not hmac.compare_digest(mac.digest(), sig):
        raise HTTPException(status_code=400, detail="Invalid state signature")

    try:
        payload = json.loads(body.decode("utf-8"))
        tenant_id_str = payload["tenant_id"]
        return UUID(tenant_id_str)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid state payload")


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

class CRMConnectInitResponse(BaseModel):
    authorization_url: str


class CRMConnectionStatus(BaseModel):
    tenant_id: UUID
    crm_system: CRMSystem
    is_enabled: bool
    expires_at: Optional[datetime] = None
    scope: Optional[str] = None


class HubSpotOAuthCallbackParams(BaseModel):
    code: str
    state: str
    actor: Optional[str] = None


# ---------------------------------------------------------------------------
# HubSpot Connect Flow
# ---------------------------------------------------------------------------

@tenant_crm_router.post(
    "/{tenant_id}/crm/hubspot/connect/initiate",
    response_model=CRMConnectInitResponse,
)
async def initiate_hubspot_connect(
    tenant_id: UUID = Depends(ensure_path_tenant_matches_token),
    token: TokenData = Depends(get_current_token),
) -> CRMConnectInitResponse:
    state = _encode_oauth_state(tenant_id)
    url = hubspot_oauth_client.build_authorization_url(state=state)
    return CRMConnectInitResponse(authorization_url=url)


@tenant_crm_router.post(
    "/{tenant_id}/crm/hubspot/oauth/callback",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def hubspot_oauth_callback(
    payload: HubSpotOAuthCallbackParams,
    tenant_id: UUID = Depends(ensure_path_tenant_matches_token),
    token: TokenData = Depends(get_current_token),
    store: CRMCredentialsStore = Depends(get_crm_credentials_store),
):
    state_tenant_id = _decode_and_verify_oauth_state(payload.state or "")
    if state_tenant_id != tenant_id:
        raise HTTPException(status_code=400, detail="Invalid state for tenant")

    token_resp = await hubspot_oauth_client.exchange_code_for_tokens(payload.code)

    info = hubspot_oauth_client.token_response_to_connection_info(
        tenant_id=tenant_id,
        crm_system=CRMSystem.HUBSPOT,
        token=token_resp,
        actor=payload.actor or token.sub,
    )

    await store.upsert_credentials(info)
    return


# ---------------------------------------------------------------------------
# Status & Disconnect
# ---------------------------------------------------------------------------

@tenant_crm_router.get(
    "/{tenant_id}/crm/hubspot",
    response_model=CRMConnectionStatus,
)
async def get_hubspot_status(
    tenant_id: UUID = Depends(ensure_path_tenant_matches_token),
    token: TokenData = Depends(get_current_token),
    store: CRMCredentialsStore = Depends(get_crm_credentials_store),
):
    info = await store.get_credentials(tenant_id, CRMSystem.HUBSPOT)
    if not info:
        raise HTTPException(
            status_code=404,
            detail="No HubSpot connection for this tenant",
        )

    return CRMConnectionStatus(
        tenant_id=info.tenant_id,
        crm_system=info.crm_system,
        is_enabled=info.is_enabled,
        expires_at=info.expires_at,
        scope=info.scope,
    )


@tenant_crm_router.delete(
    "/{tenant_id}/crm/hubspot",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def disconnect_hubspot(
    tenant_id: UUID = Depends(ensure_path_tenant_matches_token),
    token: TokenData = Depends(get_current_token),
    store: CRMCredentialsStore = Depends(get_crm_credentials_store),
):
    await store.disable_credentials(tenant_id, CRMSystem.HUBSPOT)
    return


# ---------------------------------------------------------------------------
# Debug-Endpunkt
# ---------------------------------------------------------------------------

@tenant_crm_router.get("/{tenant_id}/crm/hubspot/authorize")
async def authorize_hubspot_debug(
    tenant_id: UUID = Depends(ensure_path_tenant_matches_token),
    token: TokenData = Depends(get_current_token),
):
    return {
        "tenant_id": str(tenant_id),
        "subject": token.sub,
        "scopes": token.scopes,
    }
