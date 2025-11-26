# app/api/admin_crm_router.py

from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, Request
from pydantic import BaseModel

from app.db.database import Database
from app.integrations.credentials.crm_credentials_store import (
    CRMCredentialsStore,
    CRMConnectionInfo,
)

admin_crm_router = APIRouter(
    prefix="/admin",
    tags=["admin-crm"],
)


# ✓ Holt die DB-Instanz aus app.state.db
async def get_db(request: Request) -> Database:
    return request.app.state.db


def get_crm_credentials_store(db: Database = Depends(get_db)) -> CRMCredentialsStore:
    return CRMCredentialsStore(db)


class AdminCRMCredentialsIn(BaseModel):
    crm_system: str                 # z.B. "hubspot"
    access_token: str
    refresh_token: Optional[str] = None
    expires_at: Optional[datetime] = None
    token_type: Optional[str] = "bearer"
    scope: Optional[str] = None
    is_enabled: bool = True

    created_by: Optional[str] = None
    modified_by: Optional[str] = None


class AdminCRMCredentialsStatus(BaseModel):
    tenant_id: UUID
    crm_system: str
    is_enabled: bool
    expires_at: Optional[datetime] = None
    scope: Optional[str] = None
    last_modified_time: Optional[datetime] = None
    modified_by: Optional[str] = None


@admin_crm_router.post(
    "/tenants/{tenant_id}/crm/credentials",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def upsert_crm_credentials_for_tenant(
    tenant_id: UUID,
    payload: AdminCRMCredentialsIn,
    store: CRMCredentialsStore = Depends(get_crm_credentials_store),
):
    now = datetime.now(timezone.utc)

    info = CRMConnectionInfo(
        tenant_id=tenant_id,
        crm_system=payload.crm_system,
        access_token=payload.access_token,
        refresh_token=payload.refresh_token,
        expires_at=payload.expires_at,
        token_type=payload.token_type,
        scope=payload.scope,
        is_enabled=payload.is_enabled,
        created_time=now,
        last_modified_time=now,
        created_by=payload.created_by,
        modified_by=payload.modified_by,
    )

    await store.upsert_credentials(info)
    return


@admin_crm_router.get(
    "/tenants/{tenant_id}/crm/{crm_system}",
    response_model=AdminCRMCredentialsStatus,
)
async def get_crm_status_for_tenant(
    tenant_id: UUID,
    crm_system: str,
    store: CRMCredentialsStore = Depends(get_crm_credentials_store),
):
    info = await store.get_credentials(tenant_id, crm_system)
    if not info:
        raise HTTPException(status_code=404, detail="No credentials for this tenant & CRM")

    return AdminCRMCredentialsStatus(
        tenant_id=info.tenant_id,
        crm_system=info.crm_system,
        is_enabled=info.is_enabled,
        expires_at=info.expires_at,
        scope=info.scope,
        last_modified_time=info.last_modified_time,
        modified_by=info.modified_by,
    )


@admin_crm_router.delete(
    "/tenants/{tenant_id}/crm/{crm_system}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def disable_crm_for_tenant(
    tenant_id: UUID,
    crm_system: str,
    store: CRMCredentialsStore = Depends(get_crm_credentials_store),
):
    await store.disable_credentials(tenant_id, crm_system)
    return
