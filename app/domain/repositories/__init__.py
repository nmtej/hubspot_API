# app/domain/repositories/__init__.py

from .company_repository import CompanyRepository
from .contact_repository import ContactRepository
from .opportunity_repository import OpportunityRepository

__all__ = [
    "CompanyRepository",
    "ContactRepository",
    "OpportunityRepository",
]
