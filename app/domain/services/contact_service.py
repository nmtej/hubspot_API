# app/domain/services/contact_service.py
from __future__ import annotations

from typing import Optional, Sequence
from uuid import UUID

from app.domain.models.contact import Contact
from app.domain.repositories.contact_repository import ContactRepository


class ContactService:
    """
    Application-Service rund um Contacts.

    Verantwortlichkeiten:
      - Kapselt ContactRepository
      - Setzt Audit-Felder
      - Bietet einfache Query-Methoden
    """

    def __init__(self, contacts: ContactRepository) -> None:
        self._contacts = contacts

    # ------------------------------------------------------------------ #
    # Reads
    # ------------------------------------------------------------------ #

    async def get_contact(
        self,
        tenant_id: UUID,
        leadlane_contact_id: UUID,
    ) -> Optional[Contact]:
        return await self._contacts.get(tenant_id, leadlane_contact_id)

    async def list_contacts_for_tenant(
        self,
        tenant_id: UUID,
        limit: int = 100,
        offset: int = 0,
    ) -> Sequence[Contact]:
        return await self._contacts.list_for_tenant(tenant_id, limit=limit, offset=offset)

    async def list_contacts_for_company(
        self,
        tenant_id: UUID,
        leadlane_sub_company_id: UUID,
        limit: int = 100,
        offset: int = 0,
    ) -> Sequence[Contact]:
        return await self._contacts.list_for_company(
            tenant_id, leadlane_sub_company_id, limit=limit, offset=offset
        )

    # ------------------------------------------------------------------ #
    # Writes
    # ------------------------------------------------------------------ #

    async def save_contact(
        self,
        contact: Contact,
        actor: Optional[str] = None,
    ) -> Contact:
        """
        Persistiert einen Kontakt (Upsert in tmpl_c_db_contact).

        Erwartet ein fertig befülltes Contact-Domain-Objekt.
        """
        if contact.tenant_id is None:
            raise ValueError(
                "contact.tenant_id darf nicht None sein, bevor er gespeichert wird."
            )

        # Audit
        if contact.created_by is None:
            contact.created_by = actor or "system_sync"
        contact.modified_by = actor or "system_sync"

        return await self._contacts.save(contact)
