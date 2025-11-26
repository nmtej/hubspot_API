# app/integrations/crm/sync/__init__.py

"""
CRM Sync Layer.

- CRMSyncService: Orchestriert die Synchronisation zu einem bestimmten CRM-System
                  (Credentials holen, Client bauen, Links updaten).
- CRMSyncListener: Reagiert auf Domain-Events (Company/Contact/Deal geändert)
                   und stößt Syncs zu allen verbundenen CRMs eines Tenants an.
"""

from .crm_sync_service import CRMSyncService
from .crm_sync_listener import CRMSyncListener

__all__ = [
    "CRMSyncService",
    "CRMSyncListener",
]
