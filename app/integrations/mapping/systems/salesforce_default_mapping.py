# app/integrations/crm/mapping/systems/salesforce_default_mapping.py

"""
Default-Feld-Mappings für Salesforce (Standard-Objekte).

Struktur:
  SALESFORCE_DEFAULT_MAPPINGS = {
      "company": {udm_field: sf_field, ...},  # Account
      "contact": {...},                      # Contact
      "deal": {...},                         # Opportunity
  }
"""

SALESFORCE_DEFAULT_MAPPINGS = {
    "company": {
        # UDM-Feld      → SF Account.Field
        "company_name": "Name",
        "company_domain": "Website",
        "company_industry": "Industry",
        "company_employee_count": "NumberOfEmployees",
        "company_city": "BillingCity",
        "company_country": "BillingCountry",
    },
    "contact": {
        "first_name": "FirstName",
        "last_name": "LastName",
        "email": "Email",
        "phone": "Phone",
        "mobile_phone": "MobilePhone",
        "job_title": "Title",
    },
    "deal": {
        "deal_name": "Name",
        "deal_amount": "Amount",
        "deal_stage": "StageName",
        "close_date": "CloseDate",
        "deal_pipeline": "LeadSource",  # oder eigenes Feld
    },
    "activity": {
        # Hier könnte man z.B. Task/Activity-Felder abbilden
        "activity_subject": "Subject",
        "activity_type": "Type",
        "activity_timestamp": "ActivityDate",
        "activity_description": "Description",
    },
}
