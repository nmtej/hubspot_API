# app/integrations/__init__.py

"""
Integrationen zu externen Systemen.

Aktuell:
- CRM-Integrationen (HubSpot, Salesforce, SAP B1)
- Field-Mapping & Link-Layer
- Sync-Layer
- Credential-Store
"""

from .crm import (
    CRMSystem,
    CRMClient,
    CRMCompanyPayload,
    CRMContactPayload,
    CRMDealPayload,
    CRMActivityPayload,
    CRMSyncResult,
    CRMSyncError,
    create_crm_client,
    register_crm_client,
    get_registered_systems,
    CRMClientConfig,
    HubSpotCRMClient,
    SalesforceCRMClient,
    SAPB1CRMClient,
)
from .mapping import (
    CRMFieldMappingsRepository,
    CRMFieldMappingRecord,
    CRMAccountLinksRepository,
    CRMAccountLink,
    CRMContactLinksRepository,
    CRMContactLink,
    CRMOpportunityLinksRepository,
    CRMOpportunityLink,
    CRMFieldMappingEngine,
)
from .sync import (
    CRMSyncService,
    CRMSyncListener,
)
from .credentials import (
    CRMCredentialsStore,
    CRMConnectionInfo,
)

__all__ = [
    # CRM Core
    "CRMSystem",
    "CRMClient",
    "CRMCompanyPayload",
    "CRMContactPayload",
    "CRMDealPayload",
    "CRMActivityPayload",
    "CRMSyncResult",
    "CRMSyncError",
    "create_crm_client",
    "register_crm_client",
    "get_registered_systems",
    "CRMClientConfig",
    "HubSpotCRMClient",
    "SalesforceCRMClient",
    "SAPB1CRMClient",

    # Mapping / Links
    "CRMFieldMappingsRepository",
    "CRMFieldMappingRecord",
    "CRMAccountLinksRepository",
    "CRMAccountLink",
    "CRMContactLinksRepository",
    "CRMContactLink",
    "CRMOpportunityLinksRepository",
    "CRMOpportunityLink",
    "CRMFieldMappingEngine",

    # Sync
    "CRMSyncService",
    "CRMSyncListener",

    # Credentials
    "CRMCredentialsStore",
    "CRMConnectionInfo",
]
