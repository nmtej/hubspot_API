# app/api/schemas/crm_field_mapping.py

from typing import Literal, Optional
from uuid import UUID

from pydantic import BaseModel, Field, validator

from app.integrations.crm.crm_types import CRMSystem


ObjectType = Literal["company", "contact", "opportunity", "activity"]


class CRMFieldMappingBase(BaseModel):
    object_type: ObjectType
    udm_field_name: str = Field(..., min_length=1, max_length=200)
    crm_field_name: str = Field(..., min_length=1, max_length=200)
    is_active: bool = True

    @validator("udm_field_name", "crm_field_name")
    @classmethod
    def strip_and_validate(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("must not be empty")
        return v


class CRMFieldMappingCreate(CRMFieldMappingBase):
    """Payload für POST (Mapping anlegen)."""
    pass


class CRMFieldMappingUpdate(BaseModel):
    """Payload für PATCH (Mapping teilweise aktualisieren)."""

    crm_field_name: Optional[str] = Field(None, min_length=1, max_length=200)
    is_active: Optional[bool] = None

    @validator("crm_field_name")
    def strip_and_validate(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        v = v.strip()
        if not v:
            raise ValueError("must not be empty")
        return v


class CRMFieldMappingOut(CRMFieldMappingBase):
    """Response-Modell für ein einzelnes Mapping."""

    id: int
    tenant_id: UUID
    crm_system: CRMSystem

    class Config:
        orm_mode = True


class CRMFieldMappingsResponse(BaseModel):
    """Response-Modell für Liste von Mappings pro Tenant + CRM."""

    tenant_id: UUID
    crm_system: CRMSystem
    mappings: list[CRMFieldMappingOut]
