# app/integrations/crm/mapping/systems/sap_b1_default_mapping.py

"""
Default-Feld-Mappings für SAP Business One (Service Layer).

- company → BusinessPartners
- contact → ContactEmployees
- deal   → SalesOpportunities
"""

SAP_B1_DEFAULT_MAPPINGS = {
    "company": {
        # UDM-Feld      → BusinessPartners.Field
        "company_name": "CardName",
        "company_domain": "Website",        # je nach Customizing
        "company_industry": "Industry",
        "company_city": "MailCity",
        "company_country": "MailCountry",
    },
    "contact": {
        # UDM-Feld      → ContactEmployees.Field
        "first_name": "FirstName",
        "last_name": "LastName",
        "email": "E_Mail",
        "phone": "Phone1",
        "mobile_phone": "MobilePhone",
        "job_title": "Position",
    },
    "deal": {
        # UDM-Feld      → SalesOpportunities.Field
        "deal_name": "Name",
        "deal_amount": "MaxLocalTotal",
        "deal_stage": "CurrentStageNumber",  # oder anderes Feld
        "close_date": "ClosingDate",
    },
    "activity": {
        # Könnte auf Activities / ActivitiesService gemappt werden
        "activity_subject": "Details",
        "activity_type": "ActivityType",
        "activity_timestamp": "StartDate",
    },
}
