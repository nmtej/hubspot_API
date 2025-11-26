# app/domain/models/contact.py
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
from uuid import UUID


@dataclass
class Contact:
    """
    Tenant-spezifische Sicht auf einen Kontakt.

    Aggregiert direkt die Spalten aus:
      - public.tmpl_c_db_contact

    WICHTIG:
    - Feldnamen entsprechen bewusst den Spaltennamen in der DB.
    - Wir ergänzen nur tenant_id als UDM-Feld.
    """

    # === LeadLane / Tenant Identität ===
    tenant_id: UUID                          # Zusatzfeld im UDM, nicht in der Tabelle
    leadlane_contact_id: UUID                # PK in tmpl_c_db_contact

    # === Lusha / Enrichment ===
    lusha_contact_id: Optional[str] = None
    lusha_record_id: Optional[str] = None
    lusha_contact_search_payload: Optional[str] = None

    # === Personendaten ===
    contact_first_name: Optional[str] = None
    contact_last_name: Optional[str] = None
    contact_department: Optional[str] = None
    contact_job_title: Optional[str] = None
    contact_seniority: Optional[str] = None

    # === Verfügbarkeits-Flags ===
    contact_email_available: Optional[bool] = None
    contact_phone_available: Optional[bool] = None

    # === Kontaktinformationen ===
    contact_email_1: Optional[str] = None
    contact_email_2: Optional[str] = None
    contact_phone_1: Optional[str] = None
    contact_phone_2: Optional[str] = None
    contact_phone_3: Optional[str] = None

    # === Validierungsstatus (Enums in DB, hier als str) ===
    contact_phone_1_validation: Optional[str] = "validation_open"
    contact_phone_2_validation: Optional[str] = "validation_open"
    contact_phone_3_validation: Optional[str] = "validation_open"
    contact_email_1_validation: Optional[str] = "validation_open"
    contact_email_2_validation: Optional[str] = "validation_open"
    data_validation_status: Optional[str] = "validation_open"

    # === Lead-/Sales-Status ===
    leadstatus: str = "new_not_contacted"       # leadstatus_enum in der DB
    loss_reason: Optional[str] = None

    assigned_outreach_role: Optional[str] = None        # outreach_role_enum
    assignment_reason_chatgpt: Optional[str] = None

    notes: Optional[str] = None

    # === Beziehung zur Company ===
    leadlane_sub_company_id: Optional[UUID] = None      # FK auf central_database_sub_company.leadlane_sub_company_id

    # === LinkedIn & Location ===
    linkedin_url: Optional[str] = None
    location_country: Optional[str] = None
    location_country_iso: Optional[str] = None
    location_city: Optional[str] = None

    # === Audit / Timestamps ===
    created_time: datetime = field(default_factory=datetime.utcnow)
    last_modified_time: datetime = field(default_factory=datetime.utcnow)
    created_by: Optional[str] = "system_sync"
    modified_by: Optional[str] = "system_sync"
