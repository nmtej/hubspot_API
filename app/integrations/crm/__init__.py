# app/integrations/crm/__init__.py

"""
CRM Integrations Root Package.

Dieses Paket enthält:
- CRMClient (generischer Client)
- crm_client_factory (Factory, um pro CRM-System den passenden Client zu machen)
- crm_types (Payload-Objekte & CRMSystem Enum)
- Submodule für konkrete CRM-Integrationen (HubSpot, Salesforce, SAP B1)
  Diese werden beim Import automatisch in der Factory registriert.
"""

# Core Types
from .crm_types import (
    CRMSystem,
    CRMCompanyPayload,
    CRMContactPayload,
    CRMDealPayload,
    CRMActivityPayload,
    CRMSyncResult,
    CRMSyncError,
)

# CRMClient Interface
from .crm_client import CRMClient

# Factory
from .crm_client_factory import (
    create_crm_client,
    register_crm_client,
    get_registered_systems,
    CRMClientConfig,
)

# Concrete Submodules (important: importing triggers factory registration)
from .hubspot import HubSpotCRMClient
from .salesforce import SalesforceCRMClient
from .sap_b1 import SAPB1CRMClient

__all__ = [
    # Core Types
    "CRMSystem",
    "CRMCompanyPayload",
    "CRMContactPayload",
    "CRMDealPayload",
    "CRMActivityPayload",
    "CRMSyncResult",
    "CRMSyncError",

    # CRMClient interface
    "CRMClient",

    # Factory
    "create_crm_client",
    "register_crm_client",
    "get_registered_systems",
    "CRMClientConfig",

    # Concrete CRM client classes
    "HubSpotCRMClient",
    "SalesforceCRMClient",
    "SAPB1CRMClient",
]
