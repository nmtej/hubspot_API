# app/integrations/crm/hubspot/hubspot_refresh.py
from __future__ import annotations

from app.integrations.credentials.crm_credentials_store import CRMConnectionInfo
from app.integrations.crm.hubspot.hubspot_auth import HubSpotOAuthClient


hubspot_oauth_client = HubSpotOAuthClient()


async def refresh_hubspot_connection(info: CRMConnectionInfo) -> CRMConnectionInfo:
    """
    Refresh-Funktion für HubSpot, die von CRMCredentialsStore.get_active_credentials
    aufgerufen werden kann.
    """
    if info.refresh_token is None:
        raise ValueError("No refresh token available for HubSpot connection")

    token_resp = await hubspot_oauth_client.refresh_access_token(info.refresh_token)

    return hubspot_oauth_client.token_response_to_connection_info(
        tenant_id=info.tenant_id,
        crm_system=info.crm_system,
        token=token_resp,
        actor=info.created_by or "system",
    )
