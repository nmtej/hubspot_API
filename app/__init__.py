# app/__init__.py

"""
Top-Level Application Package.

Hier wird aktuell nur die Factory-Funktion `create_app` aus main.py
re-exportiert, damit man z. B. in Tests oder Skripten einfach:

    from app import create_app

schreiben kann.
"""

from .main import create_app

__all__ = ["create_app"]
