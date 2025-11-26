# app/integrations/crm/salesforce/__init__.py
from .salesforce_auth import SalesforceCredentials, SalesforceAuthError
from .salesforce_api import SalesforceAPI, SalesforceAPIError
from .salesforce_client import SalesforceCRMClient  # side-effect: Factory-Registration

__all__ = [
    "SalesforceCredentials",
    "SalesforceAuthError",
    "SalesforceAPI",
    "SalesforceAPIError",
    "SalesforceCRMClient",
]
