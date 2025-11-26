# app/integrations/crm/crm_client_factory.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict, Mapping
from uuid import UUID

from app.integrations.crm.crm_client import CRMClient
from app.integrations.crm.crm_types import CRMSystem
from app.integrations.credentials.crm_credentials_store import CRMCredentialsStore
from app.integrations.crm.hubspot.hubspot_client import HubSpotClient
from app.integrations.mapping import CRMFieldMappingEngine


@dataclass
class CRMClientConfig:
    """Lightweight config object used by some CRM client factories.

    In this simplified setup we only really need tenant_id and a credentials mapping.
    """
    tenant_id: UUID
    credentials: Mapping[str, Any]


# Internal registry: CRMSystem -> factory(CRMClientConfig) -> CRMClient
_CRM_REGISTRY: Dict[CRMSystem, Callable[[CRMClientConfig], CRMClient]] = {}


def register_crm_client(system: CRMSystem, factory: Callable[[CRMClientConfig], CRMClient]) -> None:
    """Compatibility hook used by Salesforce/SAP modules.

    They call register_crm_client(CRMSystem.X, factory). We keep a small
    registry so imports succeed, even if we don't actively use all systems.
    """
    _CRM_REGISTRY[system] = factory


def get_registered_systems() -> Dict[CRMSystem, Callable[[CRMClientConfig], CRMClient]]:
    """Return a copy of the internal registry (mainly for debugging)."""
    return dict(_CRM_REGISTRY)


def create_crm_client(
    *,
    crm_system: CRMSystem,
    tenant_id: UUID,
    credentials_store: CRMCredentialsStore,
    mapping_engine: CRMFieldMappingEngine,
) -> CRMClient:
    """Return a CRM-specific client for the given tenant.

    For now we only actively implement HubSpot here. Other systems may still
    register factories via `register_crm_client`, but they are optional.
    """
    if crm_system == CRMSystem.HUBSPOT:
        return HubSpotClient(
            tenant_id=tenant_id,
            credentials_store=credentials_store,
            mapping_engine=mapping_engine,
        )

    # If a factory for the given system was registered, try to use it
    factory = _CRM_REGISTRY.get(crm_system)
    if factory is not None:
        # Minimal config: we don't yet integrate credentials_store for these systems
        config = CRMClientConfig(tenant_id=tenant_id, credentials={})
        return factory(config)

    raise NotImplementedError(f"CRM client for system '{crm_system}' is not implemented yet.")
