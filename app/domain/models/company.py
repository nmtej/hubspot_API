from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Optional, List, Dict, Any
from uuid import UUID


@dataclass
class Company:
    """
    Tenant-spezifische Sicht auf eine Sub-Company (Account).
    Aggregiert:
      - central_database_sub_company
      - tmpl_c_db_sub_company

    WICHTIG:
    - Feldnamen entsprechen bewusst den Spaltennamen in der DB.
    - Repräsentiert IMMER eine SubCompany (kein Parent-Account).
    """

    # === LeadLane / Tenant Identität ===
    tenant_id: UUID                             # zusätzliches Feld, nicht in den DB-Tabellen
    leadlane_sub_company_id: UUID              # PK in central_database_sub_company & tmpl_c_db_sub_company

    # === Beziehungen / Hierarchie ===
    parent_leadlane_account_id: UUID           # central_database_sub_company.parent_leadlane_account_id (-> central_database_parent_company)
    leadlane_parent_company_id: UUID           # tmpl_c_db_sub_company.leadlane_parent_company_id (-> tmpl_c_db_parent_company)

    # === Stammdaten / Identity (zentral & tmpl) ===
    company_name: str                           # central_database_sub_company.company_name / tmpl_c_db_sub_company.company_name
    business_description: Optional[str] = None  # central_database_sub_company.business_description / tmpl_c_db_sub_company.business_description
    address_line_1: Optional[str] = None        # central_database_sub_company.address_line_1
    city: Optional[str] = None                  # central_database_sub_company.city
    postal_code: Optional[str] = None           # central_database_sub_company.postal_code
    country_region: Optional[str] = None        # central_database_sub_company.country_region / tmpl_c_db_sub_company.country_region
    entity_type: Optional[str] = None           # central_database_sub_company.entity_type
    registration_number_1: Optional[str] = None # central_database_sub_company.registration_number_1
    reporting_currency: Optional[str] = None    # central_database_sub_company.reporting_currency
    year_founded: Optional[int] = None          # central_database_sub_company.year_founded

    url: Optional[str] = None                   # central_database_sub_company.url / tmpl_c_db_sub_company.url
    company_emails: Optional[str] = None        # central_database_sub_company.company_emails
    phone: Optional[str] = None                 # central_database_sub_company.phone
    phone_alt: Optional[str] = None             # central_database_sub_company.phone_alt
    website: Optional[str] = None               # central_database_sub_company.website
    email_address: Optional[str] = None         # central_database_sub_company.email_address
    linkedin_account: Optional[str] = None      # central_database_sub_company.linkedin_account

    # === Unternehmensgröße / Zahlen (zentral) ===
    sales_eur: Optional[Decimal] = None                      # central_database_sub_company.sales_eur
    sales_total: Optional[Decimal] = None                    # central_database_sub_company.sales_total
    assets_eur: Optional[Decimal] = None                     # central_database_sub_company.assets_eur
    employees_total: Optional[int] = None                    # central_database_sub_company.employees_total
    corporate_family_members: Optional[int] = None           # central_database_sub_company.corporate_family_members

    employees_blended_sites: Optional[int] = None            # central_database_sub_company.employees_blended_sites
    employees_domestic_ultimate_total: Optional[int] = None  # central_database_sub_company.employees_domestic_ultimate_total
    employees_global_ultimate_total: Optional[int] = None    # central_database_sub_company.employees_global_ultimate_total
    employees_single_site: Optional[int] = None              # central_database_sub_company.employees_single_site

    equity_ratio_pct: Optional[Decimal] = None               # central_database_sub_company.equity_ratio_pct
    net_worth_pct: Optional[Decimal] = None                  # central_database_sub_company.net_worth_pct
    net_worth_eur: Optional[Decimal] = None                  # central_database_sub_company.net_worth_eur
    operating_profit_eur: Optional[Decimal] = None           # central_database_sub_company.operating_profit_eur
    pre_tax_profit_eur: Optional[Decimal] = None             # central_database_sub_company.pre_tax_profit_eur

    sales_domestic_ultimate_total_eur: Optional[Decimal] = None          # central_database_sub_company.sales_domestic_ultimate_total_eur
    sales_global_ultimate_total_eur: Optional[Decimal] = None            # central_database_sub_company.sales_global_ultimate_total_eur
    sales_global_ultimate_total_as_reported: Optional[Decimal] = None    # central_database_sub_company.sales_global_ultimate_total_as_reported

    # === Branchenklassifikationen (zentral) ===
    anzsic_2006_code: Optional[str] = None               # central_database_sub_company.anzsic_2006_code
    anzsic_2006_description: Optional[str] = None        # central_database_sub_company.anzsic_2006_description
    isic_rev_4_code: Optional[str] = None                # central_database_sub_company.isic_rev_4_code
    isic_rev_4_description: Optional[str] = None         # central_database_sub_company.isic_rev_4_description
    nace_rev_2_code: Optional[str] = None                # central_database_sub_company.nace_rev_2_code
    nace_rev_2_description: Optional[str] = None         # central_database_sub_company.nace_rev_2_description
    naics_2022_code: Optional[str] = None                # central_database_sub_company.naics_2022_code
    naics_2022_description: Optional[str] = None         # central_database_sub_company.naics_2022_description
    uk_sic_2007_code: Optional[str] = None               # central_database_sub_company.uk_sic_2007_code
    uk_sic_2007_description: Optional[str] = None        # central_database_sub_company.uk_sic_2007_description
    us_8_digit_sic_code: Optional[str] = None            # central_database_sub_company.us_8_digit_sic_code
    us_8_digit_sic_description: Optional[str] = None     # central_database_sub_company.us_8_digit_sic_description
    us_sic_1987_code: Optional[str] = None               # central_database_sub_company.us_sic_1987_code
    us_sic_1987_description: Optional[str] = None        # central_database_sub_company.us_sic_1987_description

    dnb_hoovers_industry: Optional[str] = None           # central_database_sub_company.dnb_hoovers_industry
    duns_number: Optional[str] = None                    # central_database_sub_company.duns_number

    # === Konzernstruktur (zentral) ===
    domestic_ultimate_company: Optional[str] = None            # central_database_sub_company.domestic_ultimate_company
    domestic_ultimate_duns_number: Optional[str] = None        # central_database_sub_company.domestic_ultimate_duns_number
    global_ultimate_company: Optional[str] = None              # central_database_sub_company.global_ultimate_company
    global_ultimate_country_region: Optional[str] = None       # central_database_sub_company.global_ultimate_country_region
    global_ultimate_duns_number: Optional[str] = None          # central_database_sub_company.global_ultimate_duns_number
    parent_company: Optional[str] = None                       # central_database_sub_company.parent_company
    parent_country_region: Optional[str] = None                # central_database_sub_company.parent_country_region
    parent_duns_number: Optional[str] = None                   # central_database_sub_company.parent_duns_number

    international_region: Optional[str] = None                 # central_database_sub_company.international_region
    is_headquarters: Optional[bool] = None                     # central_database_sub_company.is_headquarters
    state_or_province: Optional[str] = None                    # central_database_sub_company.state_or_province

    # === Beschreibungen & Metainfos (zentral) ===
    company_name_email: Optional[str] = None                   # central_database_sub_company.company_name_email
    competitors: Optional[str] = None                          # central_database_sub_company.competitors
    company_description_leadlane: Optional[str] = None         # central_database_sub_company.company_description_leadlane
    account_summary_gpt: Optional[str] = None                  # central_database_sub_company.account_summary_gpt
    source: Optional[str] = None                               # central_database_sub_company.source

    # === Betriebsstatus (zentral) ===
    unit_type: Optional[str] = None                            # central_database_sub_company.unit_type (enum in DB)
    is_operational: Optional[bool] = None                      # central_database_sub_company.is_operational

    # === Lusha / Enrichment (zentral) ===
    lusha_accounts: List[Dict[str, Any]] = field(default_factory=list)  # central_database_sub_company.lusha_accounts (jsonb array)

    # === Tenant-spezifische Sales-Felder (tmpl_c_db_sub_company) ===
    lifecycle_phase: str = "new_not_contacted"            # tmpl_c_db_sub_company.lifecycle_phase
    loss_reason: Optional[str] = None                     # tmpl_c_db_sub_company.loss_reason

    contacts_backlog: int = 0                             # tmpl_c_db_sub_company.contacts_backlog
    contacts_total: int = 0                               # tmpl_c_db_sub_company.contacts_total
    contacts_active: int = 0                              # tmpl_c_db_sub_company.contacts_active
    contacts_validation: int = 0                          # tmpl_c_db_sub_company.contacts_validation

    date_last_lusha_contact_search: Optional[datetime] = None   # tmpl_c_db_sub_company.date_last_lusha_contact_search

    responsible_sdr_id: Optional[UUID] = None             # tmpl_c_db_sub_company.responsible_sdr_id

    # === Timestamps & Audit (zentral + tmpl) ===
    # Wir führen sie zusammen, da zentrale & tmpl Tabellen gleichnamige Felder nutzen.
    created_time: datetime = field(default_factory=datetime.utcnow)   # created_time (central + tmpl)
    last_modified_time: datetime = field(default_factory=datetime.utcnow)  # last_modified_time (central + tmpl)
    created_by: Optional[str] = None                                # created_by (central + tmpl)
    modified_by: Optional[str] = None                               # modified_by (central + tmpl)
