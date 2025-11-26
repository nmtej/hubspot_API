# app/domain/models/__init__.py

from .company import Company
from .contact import Contact
from .opportunity import Opportunity

__all__ = [
    "Company",
    "Contact",
    "Opportunity",
]
