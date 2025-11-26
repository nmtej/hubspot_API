# app/domain/repositories/contact_repository.py
from __future__ import annotations

from typing import Optional, Sequence, Mapping, Any
from uuid import UUID

from app.domain.models.contact import Contact
from app.db.database import Database  # dein DB-Wrapper (fetch_one, fetch_all, execute)


class ContactRepository:
    """
    Konkretes Contact-Repository für Supabase/Postgres.

    Nutzt:
      - public.tmpl_c_db_contact
    """

    def __init__(self, db: Database) -> None:
        self._db = db

    # -------------------------------------------------------------------------
    # Public API
    # -------------------------------------------------------------------------

    async def get(
        self,
        tenant_id: UUID,
        leadlane_contact_id: UUID,
    ) -> Optional[Contact]:
        row = await self._db.fetch_one(
            _SELECT_CONTACT_BY_ID_SQL,
            {"leadlane_contact_id": str(leadlane_contact_id)},
        )
        if row is None:
            return None

        return self._row_to_contact(row, tenant_id=tenant_id)

    async def list_for_company(
        self,
        tenant_id: UUID,
        leadlane_sub_company_id: UUID,
        limit: int = 100,
        offset: int = 0,
    ) -> Sequence[Contact]:
        rows = await self._db.fetch_all(
            _SELECT_CONTACTS_FOR_COMPANY_SQL,
            {
                "leadlane_sub_company_id": str(leadlane_sub_company_id),
                "limit": limit,
                "offset": offset,
            },
        )
        return [self._row_to_contact(r, tenant_id=tenant_id) for r in rows]

    async def save(self, contact: Contact) -> Contact:
        """
        Upsert eines Kontakts in tmpl_c_db_contact.

        Audit:
        - created_time/last_modified_time kommen aus der DB (DEFAULT/now()).
        - created_by/modified_by kommen aus dem Service (actor).
        """
        await self._db.execute(
            _UPSERT_CONTACT_SQL,
            {
                "leadlane_contact_id": str(contact.leadlane_contact_id),
                "lusha_contact_id": contact.lusha_contact_id,
                "lusha_record_id": contact.lusha_record_id,
                "lusha_contact_search_payload": contact.lusha_contact_search_payload,
                "contact_first_name": contact.contact_first_name,
                "contact_last_name": contact.contact_last_name,
                "contact_department": contact.contact_department,
                "contact_job_title": contact.contact_job_title,
                "contact_seniority": contact.contact_seniority,
                "contact_email_available": contact.contact_email_available,
                "contact_phone_available": contact.contact_phone_available,
                "contact_email_1": contact.contact_email_1,
                "contact_email_2": contact.contact_email_2,
                "contact_phone_1": contact.contact_phone_1,
                "contact_phone_2": contact.contact_phone_2,
                "contact_phone_3": contact.contact_phone_3,
                "contact_phone_1_validation": contact.contact_phone_1_validation,
                "contact_phone_2_validation": contact.contact_phone_2_validation,
                "contact_phone_3_validation": contact.contact_phone_3_validation,
                "contact_email_1_validation": contact.contact_email_1_validation,
                "contact_email_2_validation": contact.contact_email_2_validation,
                "data_validation_status": contact.data_validation_status,
                "leadstatus": contact.leadstatus,
                "loss_reason": contact.loss_reason,
                "assigned_outreach_role": contact.assigned_outreach_role,
                "assignment_reason_chatgpt": contact.assignment_reason_chatgpt,
                "notes": contact.notes,
                "leadlane_sub_company_id": (
                    str(contact.leadlane_sub_company_id)
                    if contact.leadlane_sub_company_id
                    else None
                ),
                "linkedin_url": contact.linkedin_url,
                "location_country": contact.location_country,
                "location_country_iso": contact.location_country_iso,
                "location_city": contact.location_city,
                "created_by": contact.created_by,
                "modified_by": contact.modified_by,
            },
        )
        return contact

    # -------------------------------------------------------------------------
    # Row → Domain Mapping
    # -------------------------------------------------------------------------

    def _row_to_contact(self, row: Mapping[str, Any], tenant_id: UUID) -> Contact:
        return Contact(
            tenant_id=tenant_id,
            leadlane_contact_id=row["leadlane_contact_id"],
            lusha_contact_id=row.get("lusha_contact_id"),
            lusha_record_id=row.get("lusha_record_id"),
            lusha_contact_search_payload=row.get("lusha_contact_search_payload"),
            contact_first_name=row.get("contact_first_name"),
            contact_last_name=row.get("contact_last_name"),
            contact_department=row.get("contact_department"),
            contact_job_title=row.get("contact_job_title"),
            contact_seniority=row.get("contact_seniority"),
            contact_email_available=row.get("contact_email_available"),
            contact_phone_available=row.get("contact_phone_available"),
            contact_email_1=row.get("contact_email_1"),
            contact_email_2=row.get("contact_email_2"),
            contact_phone_1=row.get("contact_phone_1"),
            contact_phone_2=row.get("contact_phone_2"),
            contact_phone_3=row.get("contact_phone_3"),
            contact_phone_1_validation=row.get("contact_phone_1_validation"),
            contact_phone_2_validation=row.get("contact_phone_2_validation"),
            contact_phone_3_validation=row.get("contact_phone_3_validation"),
            contact_email_1_validation=row.get("contact_email_1_validation"),
            contact_email_2_validation=row.get("contact_email_2_validation"),
            data_validation_status=row.get("data_validation_status"),
            leadstatus=row.get("leadstatus", "new_not_contacted"),
            loss_reason=row.get("loss_reason"),
            assigned_outreach_role=row.get("assigned_outreach_role"),
            assignment_reason_chatgpt=row.get("assignment_reason_chatgpt"),
            notes=row.get("notes"),
            leadlane_sub_company_id=row.get("leadlane_sub_company_id"),
            linkedin_url=row.get("linkedin_url"),
            location_country=row.get("location_country"),
            location_country_iso=row.get("location_country_iso"),
            location_city=row.get("location_city"),
            created_time=row.get("created_time"),
            last_modified_time=row.get("last_modified_time"),
            created_by=row.get("created_by"),
            modified_by=row.get("modified_by"),
        )


# -------------------------------------------------------------------------
# SQL-Statements
# -------------------------------------------------------------------------

_SELECT_CONTACT_BY_ID_SQL = """
    SELECT
        leadlane_contact_id,
        lusha_contact_id,
        lusha_record_id,
        lusha_contact_search_payload,
        contact_first_name,
        contact_last_name,
        contact_department,
        contact_job_title,
        contact_seniority,
        contact_email_available,
        contact_phone_available,
        contact_email_1,
        contact_email_2,
        contact_phone_1,
        contact_phone_2,
        contact_phone_3,
        contact_phone_1_validation,
        contact_phone_2_validation,
        contact_phone_3_validation,
        contact_email_1_validation,
        contact_email_2_validation,
        data_validation_status,
        leadstatus,
        loss_reason,
        assigned_outreach_role,
        assignment_reason_chatgpt,
        notes,
        leadlane_sub_company_id,
        linkedin_url,
        location_country,
        location_country_iso,
        location_city,
        created_time,
        last_modified_time,
        created_by,
        modified_by
    FROM public.tmpl_c_db_contact
    WHERE leadlane_contact_id = :leadlane_contact_id
"""

_SELECT_CONTACTS_FOR_COMPANY_SQL = """
    SELECT
        leadlane_contact_id,
        lusha_contact_id,
        lusha_record_id,
        lusha_contact_search_payload,
        contact_first_name,
        contact_last_name,
        contact_department,
        contact_job_title,
        contact_seniority,
        contact_email_available,
        contact_phone_available,
        contact_email_1,
        contact_email_2,
        contact_phone_1,
        contact_phone_2,
        contact_phone_3,
        contact_phone_1_validation,
        contact_phone_2_validation,
        contact_phone_3_validation,
        contact_email_1_validation,
        contact_email_2_validation,
        data_validation_status,
        leadstatus,
        loss_reason,
        assigned_outreach_role,
        assignment_reason_chatgpt,
        notes,
        leadlane_sub_company_id,
        linkedin_url,
        location_country,
        location_country_iso,
        location_city,
        created_time,
        last_modified_time,
        created_by,
        modified_by
    FROM public.tmpl_c_db_contact
    WHERE leadlane_sub_company_id = :leadlane_sub_company_id
    ORDER BY created_time DESC
    LIMIT :limit OFFSET :offset
"""

_UPSERT_CONTACT_SQL = """
    INSERT INTO public.tmpl_c_db_contact (
        leadlane_contact_id,
        lusha_contact_id,
        lusha_record_id,
        lusha_contact_search_payload,
        contact_first_name,
        contact_last_name,
        contact_department,
        contact_job_title,
        contact_seniority,
        contact_email_available,
        contact_phone_available,
        contact_email_1,
        contact_email_2,
        contact_phone_1,
        contact_phone_2,
        contact_phone_3,
        contact_phone_1_validation,
        contact_phone_2_validation,
        contact_phone_3_validation,
        contact_email_1_validation,
        contact_email_2_validation,
        data_validation_status,
        leadstatus,
        loss_reason,
        assigned_outreach_role,
        assignment_reason_chatgpt,
        notes,
        leadlane_sub_company_id,
        linkedin_url,
        location_country,
        location_country_iso,
        location_city,
        created_by,
        modified_by
    )
    VALUES (
        :leadlane_contact_id,
        :lusha_contact_id,
        :lusha_record_id,
        :lusha_contact_search_payload,
        :contact_first_name,
        :contact_last_name,
        :contact_department,
        :contact_job_title,
        :contact_seniority,
        :contact_email_available,
        :contact_phone_available,
        :contact_email_1,
        :contact_email_2,
        :contact_phone_1,
        :contact_phone_2,
        :contact_phone_3,
        :contact_phone_1_validation,
        :contact_phone_2_validation,
        :contact_phone_3_validation,
        :contact_email_1_validation,
        :contact_email_2_validation,
        :data_validation_status,
        :leadstatus,
        :loss_reason,
        :assigned_outreach_role,
        :assignment_reason_chatgpt,
        :notes,
        :leadlane_sub_company_id,
        :linkedin_url,
        :location_country,
        :location_country_iso,
        :location_city,
        :created_by,
        :modified_by
    )
    ON CONFLICT (leadlane_contact_id)
    DO UPDATE SET
        lusha_contact_id = EXCLUDED.lusha_contact_id,
        lusha_record_id = EXCLUDED.lusha_record_id,
        lusha_contact_search_payload = EXCLUDED.lusha_contact_search_payload,
        contact_first_name = EXCLUDED.contact_first_name,
        contact_last_name = EXCLUDED.contact_last_name,
        contact_department = EXCLUDED.contact_department,
        contact_job_title = EXCLUDED.contact_job_title,
        contact_seniority = EXCLUDED.contact_seniority,
        contact_email_available = EXCLUDED.contact_email_available,
        contact_phone_available = EXCLUDED.contact_phone_available,
        contact_email_1 = EXCLUDED.contact_email_1,
        contact_email_2 = EXCLUDED.contact_email_2,
        contact_phone_1 = EXCLUDED.contact_phone_1,
        contact_phone_2 = EXCLUDED.contact_phone_2,
        contact_phone_3 = EXCLUDED.contact_phone_3,
        contact_phone_1_validation = EXCLUDED.contact_phone_1_validation,
        contact_phone_2_validation = EXCLUDED.contact_phone_2_validation,
        contact_phone_3_validation = EXCLUDED.contact_phone_3_validation,
        contact_email_1_validation = EXCLUDED.contact_email_1_validation,
        contact_email_2_validation = EXCLUDED.contact_email_2_validation,
        data_validation_status = EXCLUDED.data_validation_status,
        leadstatus = EXCLUDED.leadstatus,
        loss_reason = EXCLUDED.loss_reason,
        assigned_outreach_role = EXCLUDED.assigned_outreach_role,
        assignment_reason_chatgpt = EXCLUDED.assignment_reason_chatgpt,
        notes = EXCLUDED.notes,
        leadlane_sub_company_id = EXCLUDED.leadlane_sub_company_id,
        linkedin_url = EXCLUDED.linkedin_url,
        location_country = EXCLUDED.location_country,
        location_country_iso = EXCLUDED.location_country_iso,
        location_city = EXCLUDED.location_city,
        last_modified_time = now(),
        modified_by = EXCLUDED.modified_by
"""