# app/db/__init__.py

"""
Datenbank-Layer (Supabase/Postgres).

Wird von den Domain-Repositories verwendet.
"""

from .database import Database

__all__ = ["Database"]