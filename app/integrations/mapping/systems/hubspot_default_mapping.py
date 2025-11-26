# app/integrations/crm/mapping/systems/hubspot_default_mapping.py

"""
Default-Feld-Mappings für HubSpot.

Struktur:
  HUBSPOT_DEFAULT_MAPPINGS = {
      "company": {udm_field: hubspot_property, ...},
      "contact": {...},
      "deal": {...},
  }
"""

HUBSPOT_DEFAULT_MAPPINGS = {
    "company": {
        # UDM-Feld      → HubSpot-Property
        "company_name": "name",
        "company_domain": "domain",
        "company_website": "website",
        "company_industry": "industry",
        "company_employee_count": "numberofemployees",
        "company_city": "city",
        "company_country": "country",
    },
    "contact": {
        "first_name": "firstname",
        "last_name": "lastname",
        "email": "email",
        "phone": "phone",
        "job_title": "jobtitle",
        "mobile_phone": "mobilephone",
        "linkedin_profile_url": "linkedinbio",
    },
    "deal": {
        "deal_name": "dealname",
        "deal_amount": "amount",
        "deal_stage": "dealstage",
        "deal_pipeline": "pipeline",
        "close_date": "closedate",
    },
    "activity": {
        "activity_type": "hs_activity_type",
        "activity_subject": "hs_note_body",
        "activity_timestamp": "hs_timestamp",
    },
}
