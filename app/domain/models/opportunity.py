# app/domain/models/opportunity.py
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
from uuid import UUID


@dataclass
class Opportunity:
    """
    Tenant-spezifische Sicht auf eine Demo / Opportunity.

    Mapped auf:
      - public.tmpl_demo_manager

    Domain-Namen:
      - leadlane_sub_company_id (statt leadlane_account_id)
      - demo_preparation (statt demo_preperation)
    """

    # === LeadLane / Tenant Identität ===
    tenant_id: UUID
    leadlane_demo_id: UUID                   # PK in tmpl_demo_manager

    # === Beziehungen ===
    leadlane_sub_company_id: UUID            # DB: leadlane_account_id
    leadlane_contact_id: UUID
    responsible_sdr_id: Optional[UUID] = None

    # === Demo / Deal Infos ===
    demo_date: Optional[datetime] = None
    demo_invite_sent_at: Optional[datetime] = None
    demo_preparation: Optional[str] = None   # DB: demo_preperation (mit Schreibfehler)
    demo_status: Optional[str] = None        # demo_status_enum

    # === BANT-Qualifizierung ===
    bant_budget: Optional[str] = "unknown"   # bant_budget_enum
    bant_authority: Optional[str] = "unknown"
    bant_need: Optional[str] = "unknown"
    bant_timing: Optional[str] = "unknown"
    bant_comment: Optional[str] = None

    # === Audit / Timestamps ===
    created_time: datetime = field(default_factory=datetime.utcnow)
    last_modified_time: datetime = field(default_factory=datetime.utcnow)
    created_by: Optional[str] = None
    modified_by: Optional[str] = None
