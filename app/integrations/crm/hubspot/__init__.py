# app/integrations/crm/hubspot/__init__.py
from .hubspot_auth import HubSpotCredentials, HubSpotAuthError
from .hubspot_api import HubSpotAPI, HubSpotAPIError
# from .hubspot_client import HubSpotCRMClient  # import side-effect: Factory-Registration
from .hubspot_client import HubSpotClient as HubSpotCRMClient

__all__ = [
    "HubSpotCredentials",
    "HubSpotAuthError",
    "HubSpotAPI",
    "HubSpotAPIError",
    "HubSpotCRMClient",
]
