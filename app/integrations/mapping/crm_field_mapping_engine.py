# app/integrations/crm/mapping/crm_field_mapping_engine.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Mapping, Optional, Type, TypeVar
from uuid import UUID

from app.integrations.crm.crm_types import CRMSystem
from .crm_field_mappings_repository import CRMFieldMappingsRepository, CRMFieldMappingRecord
from .systems.hubspot_default_mapping import HUBSPOT_DEFAULT_MAPPINGS
from .systems.salesforce_default_mapping import SALESFORCE_DEFAULT_MAPPINGS
from .systems.sap_b1_default_mapping import SAP_B1_DEFAULT_MAPPINGS
from dataclasses import replace

T = TypeVar("T")



@dataclass(frozen=True)
class EffectiveFieldMapping:
    """
    Effektives Mapping für ein Objekt:
      - key: UDM-Feldname
      - value: CRM-Feldname
    """
    udm_to_crm: Dict[str, str]


def _get_default_mapping_for(
    crm_system: CRMSystem,
    object_type: str,
) -> Dict[str, str]:
    object_type = object_type.lower()

    if crm_system == CRMSystem.HUBSPOT:
        return HUBSPOT_DEFAULT_MAPPINGS.get(object_type, {})
    if crm_system == CRMSystem.SALESFORCE:
        return SALESFORCE_DEFAULT_MAPPINGS.get(object_type, {})
    if crm_system == CRMSystem.SAP_B1:
        return SAP_B1_DEFAULT_MAPPINGS.get(object_type, {})

    return {}


class CRMFieldMappingEngine:
    """
    Engine, um aus einem UDM-Objekt ein Properties-Dict für ein
    bestimmtes CRM-System zu bauen (UDM → CRM-Feldnamen).

    Logik:
      1. Default-Mappings pro CRM-System laden
      2. Tenant-spezifische Overrides aus dem Repository holen
      3. Defaults + Overrides mergen (tenant > global default)
      4. Attribute vom UDM-Objekt auslesen und Properties-Dict bauen
    """

    def __init__(self, mappings_repo: CRMFieldMappingsRepository) -> None:
        self._repo = mappings_repo

    async def get_effective_mapping(
        self,
        *,
        tenant_id: Optional[UUID],
        crm_system: CRMSystem,
        object_type: str,
    ) -> EffectiveFieldMapping:
        # 1. Default-Mapping
        default_mapping = dict(
            _get_default_mapping_for(crm_system, object_type)
        )  # udm_field -> crm_field

        # 2. Tenant-spezifische + globale DB-Mappings laden
        records = await self._repo.get_active_mappings_for_object(
            tenant_id=tenant_id,
            crm_system=crm_system,
            object_type=object_type,
        )

        # 3. Mergen: DB-Mappings überschreiben Defaults
        udm_to_crm = default_mapping
        for rec in records:
            # Nur outbound/bidirectional für UDM → CRM beachten
            if rec.direction in ("outbound", "bidirectional"):
                udm_to_crm[rec.udm_field] = rec.crm_field

        return EffectiveFieldMapping(udm_to_crm=udm_to_crm)

    async def map_udm_to_crm_properties(
        self,
        *,
        tenant_id: Optional[UUID],
        crm_system: CRMSystem,
        object_type: str,
        udm_object: Any,
        extra_fields: Optional[Mapping[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Baut ein CRM-Properties-Dict aus einem UDM-Objekt.

        - Liest Attribute aus udm_object via getattr
        - Nutzt EffectiveFieldMapping (UDM-Feld → CRM-Feld)
        - Fügt ggf. extra_fields (direkt CRM-Feldnamen) hinzu
        """
        effective_mapping = await self.get_effective_mapping(
            tenant_id=tenant_id,
            crm_system=crm_system,
            object_type=object_type,
        )

        properties: Dict[str, Any] = {}

        for udm_field, crm_field in effective_mapping.udm_to_crm.items():
            if not hasattr(udm_object, udm_field):
                continue

            value = getattr(udm_object, udm_field)
            # None-Werte in der Regel überspringen, um keine Felder zu "löschen"
            if value is not None:
                properties[crm_field] = value

        if extra_fields:
            properties.update(extra_fields)

        return properties

    async def map_crm_to_udm(
        self,
        *,
        tenant_id: Optional[UUID],
        crm_system: CRMSystem,
        object_type: str,
        crm_properties: Mapping[str, Any],
        udm_cls: Type[T],
        existing: Optional[T] = None,
    ) -> T:
        """
        Umkehrung von map_udm_to_crm_properties:

        - Holt das effektive Mapping für (tenant, crm_system, object_type)
          → udm_field -> crm_field
        - Invertiert das Mapping: crm_field -> udm_field
        - Baut daraus entweder ein neues UDM-Objekt oder patched ein bestehendes (existing)
        """

        effective_mapping = await self.get_effective_mapping(
            tenant_id=tenant_id,
            crm_system=crm_system,
            object_type=object_type,
        )

        # Invertierung: CRM-Feld → UDM-Feld
        crm_to_udm: Dict[str, str] = {
            crm_field: udm_field
            for udm_field, crm_field in effective_mapping.udm_to_crm.items()
        }

        patch_data: Dict[str, Any] = {}

        for crm_field, value in crm_properties.items():
            udm_field = crm_to_udm.get(crm_field)
            if udm_field is None:
                # Feld ist im Mapping nicht definiert → ignorieren
                continue
            patch_data[udm_field] = value

        if existing is not None:
            # Dataclass patchen
            return replace(existing, **patch_data)

        # Neues Objekt bauen
        return udm_cls(**patch_data)  # type: ignore[arg-type]

