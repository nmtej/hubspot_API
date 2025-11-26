# app/api/dependencies.py
from uuid import UUID

from fastapi import Depends, Request, HTTPException, Path, status

from app.db.database import Database
from app.integrations.mapping import (
    CRMFieldMappingsRepository,
    CRMFieldMappingEngine,
    CRMAccountLinksRepository,
    CRMContactLinksRepository,
    CRMOpportunityLinksRepository,
)
from app.integrations.credentials.crm_credentials_store import CRMCredentialsStore
from app.integrations.sync.crm_sync_service import CRMSyncService
from app.integrations.sync.crm_sync_listener import CRMSyncListener
from app.security.auth import TokenData, get_current_token

from app.integrations.mapping.crm_field_mappings_repository import (
    CRMFieldMappingsRepository,
)


# ---------------------------------------------------------------------------
# DB
# ---------------------------------------------------------------------------

def get_db(request: Request) -> Database:
    return request.app.state.db


# ---------------------------------------------------------------------------
# Mapping / Repositories
# ---------------------------------------------------------------------------

def get_crm_field_mappings_repo(
    db: Database = Depends(get_db),
) -> CRMFieldMappingsRepository:
    return CRMFieldMappingsRepository(db)



def get_crm_field_mapping_engine(
    repo: CRMFieldMappingsRepository = Depends(get_crm_field_mappings_repo),
) -> CRMFieldMappingEngine:
    return CRMFieldMappingEngine(repo)


def get_account_links_repo(
    db: Database = Depends(get_db),
) -> CRMAccountLinksRepository:
    return CRMAccountLinksRepository(db)


def get_contact_links_repo(
    db: Database = Depends(get_db),
) -> CRMContactLinksRepository:
    return CRMContactLinksRepository(db)


def get_opportunity_links_repo(
    db: Database = Depends(get_db),
) -> CRMOpportunityLinksRepository:
    return CRMOpportunityLinksRepository(db)


# ---------------------------------------------------------------------------
# Credentials / Sync
# ---------------------------------------------------------------------------

def get_crm_credentials_store(
    db: Database = Depends(get_db),
) -> CRMCredentialsStore:
    return CRMCredentialsStore(db)

def get_crm_field_mappings_repository(
    db: Database = Depends(get_db),
) -> CRMFieldMappingsRepository:
    return CRMFieldMappingsRepository(db=db)


def get_crm_sync_service(
    credentials_store: CRMCredentialsStore = Depends(get_crm_credentials_store),
    account_links_repo: CRMAccountLinksRepository = Depends(get_account_links_repo),
    contact_links_repo: CRMContactLinksRepository = Depends(get_contact_links_repo),
    opportunity_links_repo: CRMOpportunityLinksRepository = Depends(
        get_opportunity_links_repo
    ),
    mapping_engine: CRMFieldMappingEngine = Depends(get_crm_field_mapping_engine),
) -> CRMSyncService:
    return CRMSyncService(
        credentials_store=credentials_store,
        account_links_repo=account_links_repo,
        contact_links_repo=contact_links_repo,
        opportunity_links_repo=opportunity_links_repo,
        mapping_engine=mapping_engine,
    )


def get_crm_sync_listener(
    sync_service: CRMSyncService = Depends(get_crm_sync_service),
    credentials_store: CRMCredentialsStore = Depends(get_crm_credentials_store),
) -> CRMSyncListener:
    return CRMSyncListener(
        sync_service=sync_service,
        credentials_store=credentials_store,
    )


# ---------------------------------------------------------------------------
# Auth / Tenant-Isolation
# ---------------------------------------------------------------------------

async def get_current_tenant_id_from_token(
    token: TokenData = Depends(get_current_token),
) -> UUID:
    return token.tenant_id


async def ensure_path_tenant_matches_token(
    path_tenant_id: UUID = Path(..., alias="tenant_id"),
    token: TokenData = Depends(get_current_token),
) -> UUID:
    if path_tenant_id != token.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="tenant_mismatch",
        )
    return path_tenant_id
