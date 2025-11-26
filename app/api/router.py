# app/api/router.py
from fastapi import APIRouter
from .tenant_crm_router import router as tenant_crm_router
from .crm_webhook_router import router as crm_webhook_router
from .crm_field_mapping_router import router as crm_field_mapping_router

api_router = APIRouter()

api_router.include_router(
    tenant_crm_router,
    prefix="/tenants",
    tags=["tenant-crm"],
)

api_router.include_router(
    crm_webhook_router,
    prefix="/crm/webhooks",
    tags=["crm-webhooks"],
)

api_router.include_router(
    crm_field_mapping_router,
    prefix="/crm/field-mappings",
    tags=["crm-field-mappings"],
)
