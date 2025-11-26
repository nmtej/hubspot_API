# app/domain/events/event_bus.py
from __future__ import annotations

import asyncio
import logging
from collections import defaultdict
from typing import (
    Any,
    Awaitable,
    Callable,
    DefaultDict,
    Dict,
    Generic,
    List,
    Type,
    TypeVar,
)

from .domain_event import DomainEvent

logger = logging.getLogger(__name__)

E = TypeVar("E", bound=DomainEvent)
EventHandler = Callable[[E], Awaitable[None]]


class EventBus:
    """
    Einfacher asynchroner In-Memory EventBus.

    Features:
      - subscribe(event_type, handler)
      - unsubscribe(event_type, handler)
      - publish(event): ruft alle Handler für den konkreten Typ auf.
      - Handler werden nacheinander ausgeführt; Fehler werden geloggt,
        aber andere Handler werden trotzdem aufgerufen.

    Typische Verwendung:

        # 1) Subscriber registrieren (z. B. beim App-Startup)
        async def handle_company_updated(event: CompanyUpdatedEvent) -> None:
            ...

        event_bus.subscribe(CompanyUpdatedEvent, handle_company_updated)

        # 2) Event publizieren (z. B. im Service oder Webhook)
        await event_bus.publish(
            CompanyUpdatedEvent(tenant_id=tenant_id, company_id=company_id)
        )
    """

    def __init__(self) -> None:
        # Mapping: Event-Typ -> Liste von Handlern
        self._subscribers: DefaultDict[
            Type[DomainEvent], List[EventHandler[Any]]
        ] = defaultdict(list)

    # ------------------------------------------------------------------ #
    # Subscription-API
    # ------------------------------------------------------------------ #

    def subscribe(self, event_type: Type[E], handler: EventHandler[E]) -> None:
        """
        Registriert einen Handler für einen konkreten Event-Typ.

        Mehrfach-Registrierung desselben Handlers für denselben Typ
        wird stillschweigend ignoriert.
        """
        handlers = self._subscribers[event_type]
        if handler not in handlers:
            handlers.append(handler)
            logger.debug(
                "Subscriber %r für Event-Typ %s registriert",
                handler,
                event_type.__name__,
            )

    def unsubscribe(self, event_type: Type[E], handler: EventHandler[E]) -> None:
        """
        Entfernt einen Handler für einen Event-Typ, falls vorhanden.
        """
        handlers = self._subscribers.get(event_type, [])
        if handler in handlers:
            handlers.remove(handler)
            logger.debug(
                "Subscriber %r für Event-Typ %s entfernt",
                handler,
                event_type.__name__,
            )

    # ------------------------------------------------------------------ #
    # Publish-API
    # ------------------------------------------------------------------ #

    async def publish(self, event: E) -> None:
        """
        Publiziert ein Event an alle registrierten Handler für dessen Typ.

        - Handler werden nacheinander in der aktuellen Event-Loop ausgeführt.
        - Fehler in einem Handler werden geloggt, stoppen aber nicht die anderen.
        """
        event_type: Type[DomainEvent] = type(event)

        handlers = list(self._subscribers.get(event_type, []))

        if not handlers:
            logger.debug(
                "Event %s (%s) hat keine registrierten Subscriber",
                event.event_name,
                event_type.__name__,
            )
            return

        logger.debug(
            "Publiziere Event %s an %d Handler",
            event.event_name,
            len(handlers),
        )

        for handler in handlers:
            try:
                await handler(event)  # type: ignore[arg-type]
            except Exception:
                logger.exception(
                    "Fehler beim Verarbeiten von Event %s in Handler %r",
                    event.event_name,
                    handler,
                )

    def publish_background(self, event: E) -> None:
        """
        Komfort-Methode, um ein Event "nebenbei" zu publishen, ohne selber
        await schreiben zu müssen (z. B. in sync-Kontexten).

        Hinweis:
          - Funktioniert nur, wenn bereits eine Event-Loop läuft
            (z. B. in FastAPI-Request-Handlern).
        """
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            # Kein aktiver Loop -> wir loggen nur und tun nichts.
            logger.warning(
                "publish_background für Event %s aufgerufen, "
                "aber keine laufende Event-Loop gefunden",
                event.event_name,
            )
            return

        loop.create_task(self.publish(event))
        logger.debug(
            "Event %s asynchron in Hintergrund-Task veröffentlicht",
            event.event_name,
        )


# Globale, einfach zu importierende Instanz
event_bus = EventBus()
