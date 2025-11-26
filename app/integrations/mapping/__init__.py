# app/integrations/crm/mapping/__init__.py

"""
CRM Field Mapping & Link Layer.

- Verwalten von Feld-Mappings (UDM → CRM-Feldnamen)
- Verwalten von Link-Tabellen (LeadLane-IDs ↔ CRM-IDs)
- Engine, um aus UDM-Objekten CRM-Payloads zu bauen
"""

from .crm_field_mappings_repository import CRMFieldMappingsRepository, CRMFieldMappingRecord
from .crm_account_links_repository import CRMAccountLinksRepository, CRMAccountLink
from .crm_contact_links_repository import CRMContactLinksRepository, CRMContactLink
from .crm_opportunity_links_repository import CRMOpportunityLinksRepository, CRMOpportunityLink
from .crm_field_mapping_engine import CRMFieldMappingEngine

__all__ = [
    "CRMFieldMappingsRepository",
    "CRMFieldMappingRecord",
    "CRMAccountLinksRepository",
    "CRMAccountLink",
    "CRMContactLinksRepository",
    "CRMContactLink",
    "CRMOpportunityLinksRepository",
    "CRMOpportunityLink",
    "CRMFieldMappingEngine",
]
