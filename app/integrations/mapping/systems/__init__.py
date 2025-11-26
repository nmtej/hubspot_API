# app/integrations/crm/mapping/systems/__init__.py

"""
Default-Feld-Mappings pro CRM-System.

Die Default-Mappings werden von der CRMFieldMappingEngine verwendet
und können über die CRMFieldMappingsRepository pro Tenant überschrieben werden.
"""

from .hubspot_default_mapping import HUBSPOT_DEFAULT_MAPPINGS
from .salesforce_default_mapping import SALESFORCE_DEFAULT_MAPPINGS
from .sap_b1_default_mapping import SAP_B1_DEFAULT_MAPPINGS

__all__ = [
    "HUBSPOT_DEFAULT_MAPPINGS",
    "SALESFORCE_DEFAULT_MAPPINGS",
    "SAP_B1_DEFAULT_MAPPINGS",
]
