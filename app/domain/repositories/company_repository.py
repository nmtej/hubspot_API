# app/domain/repositories/company_repository.py
from __future__ import annotations

from typing import Optional, Sequence, Mapping, Any, List, Dict
from uuid import UUID

from app.domain.models.company import Company
from app.db.database import Database  # dein Wrapper aus app/db/database.py


class CompanyRepository:
    """
    Konkretes CompanyRepository für Supabase/Postgres.

    Nutzt:
      - central_database_sub_company
      - tmpl_c_db_sub_company

    Annahme:
      - Die tmpl_-Tabellen sind tenant-spezifisch (ein Schema/DB pro Tenant)
        ODER der tenant_id wird anderweitig aufgelöst.
      - tenant_id wird hier (noch) nur im UDM gesetzt, nicht als Filter genutzt,
        bis ihr eine explizite Tenant-Spalte eingeführt habt.
    """

    def __init__(self, db: Database) -> None:
        self._db = db

    # -------------------------------------------------------------------------
    # Public API
    # -------------------------------------------------------------------------

    async def get(
        self,
        tenant_id: UUID,
        leadlane_sub_company_id: UUID,
    ) -> Optional[Company]:
        row = await self._db.fetch_one(
            _SELECT_COMPANY_BY_ID_SQL,
            {"leadlane_sub_company_id": str(leadlane_sub_company_id)},
        )
        if row is None:
            return None

        return self._row_to_company(row, tenant_id=tenant_id)

    async def list_for_tenant(
        self,
        tenant_id: UUID,
        limit: int = 100,
        offset: int = 0,
    ) -> Sequence[Company]:
        rows = await self._db.fetch_all(
            _SELECT_COMPANIES_FOR_TENANT_SQL,
            {
                "tenant_id": str(tenant_id),
                "limit": limit,
                "offset": offset,
            },
        )
        return [self._row_to_company(row, tenant_id=tenant_id) for row in rows]


    async def save(self, company: Company) -> Company:
        """
        Persistiert die tenant-spezifische Sicht auf die Company.

        Hier konzentrieren wir uns vorrangig auf:
          - tmpl_c_db_sub_company.*
        Zentraldaten (central_database_sub_company) werden typischerweise
        nicht von diesem Pfad geschrieben.
        """
        await self._db.execute(
            _UPSERT_TMPL_SUB_COMPANY_SQL,
            {
                "leadlane_sub_company_id": str(company.leadlane_sub_company_id),
                "leadlane_parent_company_id": str(company.leadlane_parent_company_id),
                "lifecycle_phase": company.lifecycle_phase,
                "loss_reason": company.loss_reason,
                "contacts_backlog": company.contacts_backlog,
                "contacts_total": company.contacts_total,
                "contacts_active": company.contacts_active,
                "contacts_validation": company.contacts_validation,
                "date_last_lusha_contact_search": company.date_last_lusha_contact_search,
                "company_name": company.company_name,
                "business_description": company.business_description,
                "url": company.url,
                "country_region": company.country_region,
                "responsible_sdr_id": (
                    str(company.responsible_sdr_id)
                    if company.responsible_sdr_id
                    else None
                ),
                "created_by": company.created_by,
                "modified_by": company.modified_by,
            },
        )
        return company

    # -------------------------------------------------------------------------
    # Row → Domain Mapping
    # -------------------------------------------------------------------------

    def _row_to_company(self, row: Mapping[str, Any], tenant_id: UUID) -> Company:
        """
        Mappt eine Zeile aus dem SQL-Join in ein Company-UDM-Objekt.
        Alle Feldnamen in row entsprechen den Aliasen im SELECT.
        """

        lusha_accounts_value = row.get("lusha_accounts")
        if lusha_accounts_value is None:
            lusha_accounts: List[Dict[str, Any]] = []
        else:
            lusha_accounts = lusha_accounts_value  # DB-Treiber mappt JSON → Python

        return Company(
            # === LeadLane/Tenant Identität ===
            tenant_id=tenant_id,
            leadlane_sub_company_id=row["leadlane_sub_company_id"],

            # Beziehungen
            parent_leadlane_account_id=row["parent_leadlane_account_id"],
            leadlane_parent_company_id=row["leadlane_parent_company_id"],

            # Stammdaten / Identity
            company_name=row["company_name"],
            business_description=row.get("business_description"),
            address_line_1=row.get("address_line_1"),
            city=row.get("city"),
            postal_code=row.get("postal_code"),
            country_region=row.get("country_region"),
            entity_type=row.get("entity_type"),
            registration_number_1=row.get("registration_number_1"),
            reporting_currency=row.get("reporting_currency"),
            year_founded=row.get("year_founded"),
            url=row.get("url"),
            company_emails=row.get("company_emails"),
            phone=row.get("phone"),
            phone_alt=row.get("phone_alt"),
            website=row.get("website"),
            email_address=row.get("email_address"),
            linkedin_account=row.get("linkedin_account"),

            # Unternehmensgröße / Zahlen
            sales_eur=row.get("sales_eur"),
            sales_total=row.get("sales_total"),
            assets_eur=row.get("assets_eur"),
            employees_total=row.get("employees_total"),
            corporate_family_members=row.get("corporate_family_members"),
            employees_blended_sites=row.get("employees_blended_sites"),
            employees_domestic_ultimate_total=row.get("employees_domestic_ultimate_total"),
            employees_global_ultimate_total=row.get("employees_global_ultimate_total"),
            employees_single_site=row.get("employees_single_site"),
            equity_ratio_pct=row.get("equity_ratio_pct"),
            net_worth_pct=row.get("net_worth_pct"),
            net_worth_eur=row.get("net_worth_eur"),
            operating_profit_eur=row.get("operating_profit_eur"),
            pre_tax_profit_eur=row.get("pre_tax_profit_eur"),
            sales_domestic_ultimate_total_eur=row.get("sales_domestic_ultimate_total_eur"),
            sales_global_ultimate_total_eur=row.get("sales_global_ultimate_total_eur"),
            sales_global_ultimate_total_as_reported=row.get("sales_global_ultimate_total_as_reported"),

            # Branchenklassifikationen
            anzsic_2006_code=row.get("anzsic_2006_code"),
            anzsic_2006_description=row.get("anzsic_2006_description"),
            isic_rev_4_code=row.get("isic_rev_4_code"),
            isic_rev_4_description=row.get("isic_rev_4_description"),
            nace_rev_2_code=row.get("nace_rev_2_code"),
            nace_rev_2_description=row.get("nace_rev_2_description"),
            naics_2022_code=row.get("naics_2022_code"),
            naics_2022_description=row.get("naics_2022_description"),
            uk_sic_2007_code=row.get("uk_sic_2007_code"),
            uk_sic_2007_description=row.get("uk_sic_2007_description"),
            us_8_digit_sic_code=row.get("us_8_digit_sic_code"),
            us_8_digit_sic_description=row.get("us_8_digit_sic_description"),
            us_sic_1987_code=row.get("us_sic_1987_code"),
            us_sic_1987_description=row.get("us_sic_1987_description"),
            dnb_hoovers_industry=row.get("dnb_hoovers_industry"),
            duns_number=row.get("duns_number"),

            # Konzernstruktur
            domestic_ultimate_company=row.get("domestic_ultimate_company"),
            domestic_ultimate_duns_number=row.get("domestic_ultimate_duns_number"),
            global_ultimate_company=row.get("global_ultimate_company"),
            global_ultimate_country_region=row.get("global_ultimate_country_region"),
            global_ultimate_duns_number=row.get("global_ultimate_duns_number"),
            parent_company=row.get("parent_company"),
            parent_country_region=row.get("parent_country_region"),
            parent_duns_number=row.get("parent_duns_number"),
            international_region=row.get("international_region"),
            is_headquarters=row.get("is_headquarters"),
            state_or_province=row.get("state_or_province"),

            # Beschreibungen & Metainfos
            company_name_email=row.get("company_name_email"),
            competitors=row.get("competitors"),
            company_description_leadlane=row.get("company_description_leadlane"),
            account_summary_gpt=row.get("account_summary_gpt"),
            source=row.get("source"),

            # Betriebsstatus
            unit_type=row.get("unit_type"),
            is_operational=row.get("is_operational"),

            # Lusha
            lusha_accounts=lusha_accounts,

            # Tenant-spezifische Sales-Felder (tmpl)
            lifecycle_phase=row["lifecycle_phase"],
            loss_reason=row.get("loss_reason"),
            contacts_backlog=row["contacts_backlog"],
            contacts_total=row["contacts_total"],
            contacts_active=row["contacts_active"],
            contacts_validation=row["contacts_validation"],
            date_last_lusha_contact_search=row.get("date_last_lusha_contact_search"),
            responsible_sdr_id=row.get("responsible_sdr_id"),

            # Timestamps & Audit
            created_time=row["created_time"],
            last_modified_time=row["last_modified_time"],
            created_by=row.get("created_by"),
            modified_by=row.get("modified_by"),
        )

    async def get_by_id(
        self,
        tenant_id: UUID,
        leadlane_sub_company_id: UUID,
    ) -> Optional[Company]:
        """
        Lädt eine Company anhand der leadlane_sub_company_id.
        """
        row = await self._db.fetch_one(
            _SELECT_COMPANY_BY_ID_SQL,
            {"leadlane_sub_company_id": str(leadlane_sub_company_id)},
        )
        if row is None:
            return None

        return self._row_to_company(row, tenant_id=tenant_id)


# -------------------------------------------------------------------------
# SQL-Statements
# -------------------------------------------------------------------------

_SELECT_BASE_COLUMNS = """
    c_sub.leadlane_sub_company_id,
    c_sub.parent_leadlane_account_id,
    t_sub.leadlane_parent_company_id,

    -- Stammdaten / Identity: Tenant-Overlay bevorzugt
    COALESCE(t_sub.company_name, c_sub.company_name) AS company_name,
    COALESCE(t_sub.business_description, c_sub.business_description) AS business_description,
    c_sub.address_line_1,
    c_sub.city,
    c_sub.postal_code,
    COALESCE(t_sub.country_region, c_sub.country_region) AS country_region,
    c_sub.entity_type,
    c_sub.registration_number_1,
    c_sub.reporting_currency,
    c_sub.sales_eur,
    c_sub.sales_total,
    c_sub.year_founded,
    COALESCE(t_sub.url, c_sub.url) AS url,
    c_sub.company_emails,
    c_sub.phone,
    c_sub.phone_alt,
    c_sub.website,
    c_sub.email_address,
    c_sub.linkedin_account,

    -- Unternehmensgröße / Zahlen
    c_sub.employees_total,
    c_sub.assets_eur,
    c_sub.corporate_family_members,
    c_sub.employees_blended_sites,
    c_sub.employees_domestic_ultimate_total,
    c_sub.employees_global_ultimate_total,
    c_sub.employees_single_site,
    c_sub.equity_ratio_pct,
    c_sub.net_worth_pct,
    c_sub.net_worth_eur,
    c_sub.operating_profit_eur,
    c_sub.pre_tax_profit_eur,
    c_sub.sales_domestic_ultimate_total_eur,
    c_sub.sales_global_ultimate_total_eur,
    c_sub.sales_global_ultimate_total_as_reported,

    -- Branchenklassifikationen
    c_sub.anzsic_2006_code,
    c_sub.anzsic_2006_description,
    c_sub.isic_rev_4_code,
    c_sub.isic_rev_4_description,
    c_sub.nace_rev_2_code,
    c_sub.nace_rev_2_description,
    c_sub.naics_2022_code,
    c_sub.naics_2022_description,
    c_sub.uk_sic_2007_code,
    c_sub.uk_sic_2007_description,
    c_sub.us_8_digit_sic_code,
    c_sub.us_8_digit_sic_description,
    c_sub.us_sic_1987_code,
    c_sub.us_sic_1987_description,
    c_sub.dnb_hoovers_industry,
    c_sub.duns_number,

    -- Konzernstruktur
    c_sub.domestic_ultimate_company,
    c_sub.domestic_ultimate_duns_number,
    c_sub.global_ultimate_company,
    c_sub.global_ultimate_country_region,
    c_sub.global_ultimate_duns_number,
    c_sub.parent_company,
    c_sub.parent_country_region,
    c_sub.parent_duns_number,
    c_sub.international_region,
    c_sub.is_headquarters,
    c_sub.state_or_province,

    -- Beschreibungen & Metainfos
    c_sub.company_name_email,
    c_sub.competitors,
    c_sub.company_description_leadlane,
    c_sub.account_summary_gpt,
    c_sub.source,

    -- Betriebsstatus
    c_sub.unit_type,
    c_sub.is_operational,

    -- Lusha / Enrichment
    c_sub.lusha_accounts,

    -- Tenant-spezifische Sales-Felder (tmpl_c_db_sub_company)
    t_sub.lifecycle_phase,
    t_sub.loss_reason,
    t_sub.contacts_backlog,
    t_sub.contacts_total,
    t_sub.contacts_active,
    t_sub.contacts_validation,
    t_sub.date_last_lusha_contact_search,
    t_sub.responsible_sdr_id,

    -- Timestamps: wir nehmen hier die tmpl_-Zeiten
    t_sub.created_time,
    t_sub.last_modified_time,
    t_sub.created_by,
    t_sub.modified_by
"""

_SELECT_COMPANY_BY_ID_SQL = f"""
    SELECT
        {_SELECT_BASE_COLUMNS}
    FROM public.central_database_sub_company AS c_sub
    JOIN public.tmpl_c_db_sub_company AS t_sub
      ON c_sub.leadlane_sub_company_id = t_sub.leadlane_sub_company_id
    WHERE c_sub.leadlane_sub_company_id = :leadlane_sub_company_id
"""

_SELECT_COMPANIES_FOR_TENANT_SQL = f"""
    SELECT
        {_SELECT_BASE_COLUMNS}
    FROM public.central_database_sub_company AS c_sub
    JOIN public.tmpl_c_db_sub_company AS t_sub
      ON c_sub.leadlane_sub_company_id = t_sub.leadlane_sub_company_id
    WHERE t_sub.tenant_id = :tenant_id
    ORDER BY t_sub.created_time DESC
    LIMIT :limit OFFSET :offset
"""


_UPSERT_TMPL_SUB_COMPANY_SQL = """
    INSERT INTO public.tmpl_c_db_sub_company (
        leadlane_sub_company_id,
        leadlane_parent_company_id,
        lifecycle_phase,
        loss_reason,
        contacts_backlog,
        contacts_total,
        contacts_active,
        contacts_validation,
        date_last_lusha_contact_search,
        company_name,
        business_description,
        url,
        country_region,
        responsible_sdr_id,
        created_by,
        modified_by
    )
    VALUES (
        :leadlane_sub_company_id,
        :leadlane_parent_company_id,
        :lifecycle_phase,
        :loss_reason,
        :contacts_backlog,
        :contacts_total,
        :contacts_active,
        :contacts_validation,
        :date_last_lusha_contact_search,
        :company_name,
        :business_description,
        :url,
        :country_region,
        :responsible_sdr_id,
        :created_by,
        :modified_by
    )
    ON CONFLICT (leadlane_sub_company_id)
    DO UPDATE SET
        lifecycle_phase = EXCLUDED.lifecycle_phase,
        loss_reason = EXCLUDED.loss_reason,
        contacts_backlog = EXCLUDED.contacts_backlog,
        contacts_total = EXCLUDED.contacts_total,
        contacts_active = EXCLUDED.contacts_active,
        contacts_validation = EXCLUDED.contacts_validation,
        date_last_lusha_contact_search = EXCLUDED.date_last_lusha_contact_search,
        company_name = EXCLUDED.company_name,
        business_description = EXCLUDED.business_description,
        url = EXCLUDED.url,
        country_region = EXCLUDED.country_region,
        responsible_sdr_id = EXCLUDED.responsible_sdr_id,
        last_modified_time = now(),
        modified_by = EXCLUDED.modified_by
"""
