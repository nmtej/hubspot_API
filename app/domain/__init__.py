# app/domain/__init__.py

"""
Domain Layer der LeadLane-Backend-Architektur.

Enthält:
    - Reine Domain-Modelle (UDM: Company, Contact, Opportunity)
    - Repositories für den Datenzugriff
    - Application-Services
    - Domain-Events & EventBus

Der Domain-Layer kennt:
    - Keine FastAPI-Details
    - Keine HTTP-Schicht
    - Keine Infrastruktur wie http Clients oder CRM APIs

Er bildet nur
    * Datenstruktur
    * Business-Logik
    * Eventing
ab — vollständig UI- und Infrastruktur-agnostisch.
"""

from .models.company import Company
from .models.contact import Contact
from .models.opportunity import Opportunity

from .repositories.company_repository import CompanyRepository
from .repositories.contact_repository import ContactRepository
from .repositories.opportunity_repository import OpportunityRepository

from .services.company_service import CompanyService
from .services.contact_service import ContactService
from .services.opportunity_service import OpportunityService

from .events.domain_event import DomainEvent
from .events.event_bus import event_bus, EventBus

__all__ = [
    # Models
    "Company",
    "Contact",
    "Opportunity",

    # Repositories
    "CompanyRepository",
    "ContactRepository",
    "OpportunityRepository",

    # Services
    "CompanyService",
    "ContactService",
    "OpportunityService",

    # Events
    "DomainEvent",
    "EventBus",
    "event_bus",
]
