# app/integrations/webhooks/webhook_idempotency_repository.py
from __future__ import annotations

from datetime import datetime
from typing import Optional

from app.db.database import Database


class WebhookIdempotencyRepository:
    """
    Speichert Webhook-Events, um Duplikate zu erkennen und
    den Verarbeitungsstatus zu tracken.
    """

    def __init__(self, db: Database) -> None:
        self._db = db

    async def try_mark_received(
        self,
        *,
        crm_system: str,
        event_id: str,
        occurred_at: Optional[datetime],
    ) -> bool:
        """
        Trägt das Event als 'received' ein.

        Rückgabe:
        - True: Event war neu (wurde eingefügt)
        - False: Event existiert bereits (Duplikat)
        """
        query = """
        INSERT INTO public.crm_webhook_events (
            crm_system, event_id, occurred_at
        )
        VALUES (:crm_system, :event_id, :occurred_at)
        ON CONFLICT (crm_system, event_id) DO NOTHING
        RETURNING crm_system, event_id;
        """
        row = await self._db.fetch_one(
            query,
            {
                "crm_system": crm_system,
                "event_id": event_id,
                "occurred_at": occurred_at,
            },
        )
        return row is not None

    async def mark_processed(
        self,
        *,
        crm_system: str,
        event_id: str,
        status: str = "processed",
        last_error: Optional[str] = None,
    ) -> None:
        query = """
        UPDATE public.crm_webhook_events
        SET processed_at = now(),
            status = :status,
            last_error = :last_error
        WHERE crm_system = :crm_system
          AND event_id = :event_id;
        """
        await self._db.execute(
            query,
            {
                "crm_system": crm_system,
                "event_id": event_id,
                "status": status,
                "last_error": last_error,
            },
        )
