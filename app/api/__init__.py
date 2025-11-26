# app/api/__init__.py

"""
API Layer der LeadLane Backend-Architektur.

Dieses Package enthält:
    - FastAPI Router für einzelne Domänen (Companies, Contacts, Opportunities, CRM usw.)
    - Webhook-Endpunkte
    - Auth-bezogene API-Routen (falls später benötigt)

Konvention:
    Jeder Router liegt in einer eigenen Datei, z. B.:

        company_router.py
        contact_router.py
        opportunity_router.py
        crm_webhook_router.py

    Und wird hier exportiert, damit main.py sie leicht importieren kann.
"""

# Beispiel: Wenn Router existieren, hier importieren:
# from .company_router import router as company_router
# from .contact_router import router as contact_router
# from .opportunity_router import router as opportunity_router
# from .crm_webhook_router import router as crm_webhook_router

__all__ = [
    # "company_router",
    # "contact_router",
    # "opportunity_router",
    # "crm_webhook_router",
]
