# app/integrations/credentials/__init__.py

"""
Credential-Management für externe Integrationen.

Aktuell:
- CRMCredentialsStore: Persistenz für CRM-Credentials pro Tenant & System.
"""

from .crm_credentials_store import CRMCredentialsStore, CRMConnectionInfo

__all__ = [
    "CRMCredentialsStore",
    "CRMConnectionInfo",
]
