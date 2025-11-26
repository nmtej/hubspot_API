# app/integrations/crm/crm_types.py
from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class CRMSystem(str, Enum):
    HUBSPOT = "hubspot"
    SALESFORCE = "salesforce"
    PIPEDRIVE = "pipedrive"
    SAP_B1 = "sap_b1"


class CRMCompanyPayload(BaseModel):
    """
    Company-/Account-Payload auf Basis eurer LeadLane-Feldnamen.
    """

    leadlane_sub_company_id: Optional[str] = None
    central_sub_company_id: Optional[str] = None
    central_parent_company_id: Optional[str] = None
    tenant_parent_company_id: Optional[str] = None

    name: str
    business_description: Optional[str] = None
    country_region: Optional[str] = None
    city: Optional[str] = None
    postal_code: Optional[str] = None
    address_line_1: Optional[str] = None

    url: Optional[str] = None
    website: Optional[str] = None
    linkedin_account: Optional[str] = None

    email_address: Optional[str] = None
    phone: Optional[str] = None
    phone_alt: Optional[str] = None

    employees_total: Optional[int] = None
    sales_eur: Optional[float] = None
    year_founded: Optional[int] = None

    primary_industry_code: Optional[str] = None
    primary_industry_system: Optional[str] = None
    duns_number: Optional[str] = None

    lifecycle_phase: Optional[str] = None
    loss_reason: Optional[str] = None
    responsible_sdr_id: Optional[str] = None

    account_summary_gpt: Optional[str] = None
    company_description_leadlane: Optional[str] = None

    properties: Dict[str, Any] = Field(default_factory=dict)


class CRMContactPayload(BaseModel):
    """
    Contact-Payload auf Basis eurer LeadLane-Feldnamen.
    """

    leadlane_contact_id: Optional[str] = None
    leadlane_sub_company_id: Optional[str] = None

    lusha_contact_id: Optional[str] = None
    lusha_record_id: Optional[str] = None

    contact_first_name: Optional[str] = None
    contact_last_name: Optional[str] = None
    contact_department: Optional[str] = None
    contact_job_title: Optional[str] = None
    contact_seniority: Optional[str] = None

    contact_email_1: Optional[str] = None
    contact_email_2: Optional[str] = None
    contact_phone_1: Optional[str] = None
    contact_phone_2: Optional[str] = None
    contact_phone_3: Optional[str] = None

    linkedin_url: Optional[str] = None
    location_country: Optional[str] = None
    location_country_iso: Optional[str] = None
    location_city: Optional[str] = None

    leadstatus: Optional[str] = None
    loss_reason: Optional[str] = None
    assigned_outreach_role: Optional[str] = None
    assignment_reason_chatgpt: Optional[str] = None
    notes: Optional[str] = None

    properties: Dict[str, Any] = Field(default_factory=dict)


class CRMDealStage(BaseModel):
    stage_id: str
    stage_name: str
    probability: Optional[float] = None


class CRMDealPayload(BaseModel):
    leadlane_demo_id: Optional[str] = None
    leadlane_account_id: Optional[str] = None
    leadlane_contact_id: Optional[str] = None

    responsible_sdr_id: Optional[str] = None

    demo_date: Optional[str] = None
    demo_invite_sent_at: Optional[str] = None
    demo_preperation: Optional[str] = None
    demo_status: Optional[str] = None

    bant_budget: Optional[str] = None
    bant_authority: Optional[str] = None
    bant_need: Optional[str] = None
    bant_timing: Optional[str] = None
    bant_comment: Optional[str] = None

    deal_name: Optional[str] = None
    pipeline_id: Optional[str] = None
    stage_id: Optional[str] = None

    properties: Dict[str, Any] = Field(default_factory=dict)


class CRMActivityType(str, Enum):
    CALL = "call"
    EMAIL = "email"
    MEETING = "meeting"
    TASK = "task"
    NOTE = "note"


class CRMActivityPayload(BaseModel):
    activity_type: CRMActivityType

    leadlane_sub_company_id: Optional[str] = None
    leadlane_contact_id: Optional[str] = None
    leadlane_demo_id: Optional[str] = None

    subject: Optional[str] = None
    body: Optional[str] = None
    timestamp: Optional[str] = None

    direction: Optional[str] = None
    status: Optional[str] = None

    properties: Dict[str, Any] = Field(default_factory=dict)


class CRMSyncError(BaseModel):
    code: Optional[str] = None
    message: str
    details: Optional[Dict[str, Any]] = None


class CRMSyncResult(BaseModel):
    """
    Standardisierte CRM-Antwort.
    """

    success: bool
    crm_system: CRMSystem
    crm_object_type: str
    crm_id: Optional[str] = None
    leadlane_id: Optional[str] = None
    errors: List[CRMSyncError] = Field(default_factory=list)
    raw_response: Optional[Dict[str, Any]] = None
