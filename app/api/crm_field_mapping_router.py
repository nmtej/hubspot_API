# app/api/crm_field_mapping_router.py
from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Path, status

from app.dependencies import (
    ensure_path_tenant_matches_token,
    get_crm_field_mappings_repository,
)
from app.api.schemas.crm_field_mapping import (
    CRMFieldMappingCreate,
    CRMFieldMappingOut,
    CRMFieldMappingUpdate,
    CRMFieldMappingsResponse,
)
from app.integrations.mapping.crm_field_mappings_repository import (
    CRMFieldMappingsRepository,
)
from app.integrations.crm.crm_types import CRMSystem

crm_field_mapping_router = APIRouter(
    prefix="/tenants/{tenant_id}/crm/field-mappings",
    tags=["crm_field_mappings"],
)


@crm_field_mapping_router.get(
    "/{crm_system}",
    response_model=CRMFieldMappingsResponse,
)
async def list_field_mappings(
    tenant_id: UUID = Depends(ensure_path_tenant_matches_token),
    crm_system: CRMSystem = Path(..., description="CRM system e.g. hubspot"),
    repo: CRMFieldMappingsRepository = Depends(get_crm_field_mappings_repository),
):
    """
    Liste aller Field-Mappings für Tenant + CRM-System.
    """
    rows = await repo.list_for_tenant_and_system(tenant_id, crm_system)
    mappings = [CRMFieldMappingOut(**row) for row in rows]
    return CRMFieldMappingsResponse(
        tenant_id=tenant_id,
        crm_system=crm_system,
        mappings=mappings,
    )


@crm_field_mapping_router.post(
    "/{crm_system}",
    response_model=CRMFieldMappingOut,
    status_code=status.HTTP_201_CREATED,
)
async def create_field_mapping(
    payload: CRMFieldMappingCreate,
    tenant_id: UUID = Depends(ensure_path_tenant_matches_token),
    crm_system: CRMSystem = Path(...),
    repo: CRMFieldMappingsRepository = Depends(get_crm_field_mappings_repository),
):
    """
    Neues Field-Mapping anlegen.

    Validation:
    - pro (tenant, crm_system, object_type) darf ein udm_field_name nicht doppelt vorkommen.
    """
    existing = await repo.list_for_tenant_and_system(tenant_id, crm_system)
    for row in existing:
        if (
            row["object_type"] == payload.object_type
            and row["udm_field_name"].lower() == payload.udm_field_name.lower()
        ):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="udm_field_name_already_mapped_for_object_type",
            )

    row = await repo.create_mapping(
        tenant_id=tenant_id,
        crm_system=crm_system,
        object_type=payload.object_type,
        udm_field_name=payload.udm_field_name,
        crm_field_name=payload.crm_field_name,
        is_active=payload.is_active,
    )
    return CRMFieldMappingOut(**row)


@crm_field_mapping_router.patch(
    "/{crm_system}/{mapping_id}",
    response_model=CRMFieldMappingOut,
)
async def update_field_mapping(
    payload: CRMFieldMappingUpdate,
    tenant_id: UUID = Depends(ensure_path_tenant_matches_token),
    crm_system: CRMSystem = Path(...),
    mapping_id: int = Path(..., ge=1),
    repo: CRMFieldMappingsRepository = Depends(get_crm_field_mappings_repository),
):
    """
    Field-Mapping teilweise aktualisieren (crm_field_name, is_active).
    """
    rows = await repo.list_for_tenant_and_system(tenant_id, crm_system)
    if not any(row["id"] == mapping_id for row in rows):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="mapping_not_found_for_tenant_and_crm",
        )

    try:
        row = await repo.update_mapping(
            mapping_id=mapping_id,
            crm_field_name=payload.crm_field_name,
            is_active=payload.is_active,
        )
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="mapping_not_found",
        )

    return CRMFieldMappingOut(**row)


@crm_field_mapping_router.delete(
    "/{crm_system}/{mapping_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_field_mapping(
    tenant_id: UUID = Depends(ensure_path_tenant_matches_token),
    crm_system: CRMSystem = Path(...),
    mapping_id: int = Path(..., ge=1),
    repo: CRMFieldMappingsRepository = Depends(get_crm_field_mappings_repository),
):
    """
    Field-Mapping löschen.

    Prüft vorher, ob das Mapping zu Tenant + CRM gehört.
    """
    rows = await repo.list_for_tenant_and_system(tenant_id, crm_system)
    if not any(row["id"] == mapping_id for row in rows):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="mapping_not_found_for_tenant_and_crm",
        )

    await repo.delete_mapping(mapping_id)
    return
