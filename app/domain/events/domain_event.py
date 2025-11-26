# app/domain/events/domain_event.py
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from uuid import UUID, uuid4


@dataclass
class DomainEvent:
    """
    Basis-Klasse für Domain-Events.

    Idee:
      - Alle Events sind Value Objects.
      - Sie haben immer eine UUID und einen Zeitstempel.
      - tenant_id ist optional (z. B. bei systemweiten Events).
      - Weitere Nutzdaten kommen in Subklassen als eigene Felder dazu.

    Beispiel für ein konkretes Event:

        @dataclass
        class CompanyUpdatedEvent(DomainEvent):
            tenant_id: UUID
            company_id: UUID
            source: str = "leadlane-backend"
    """

    id: UUID = field(default_factory=uuid4)
    occurred_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    # optionaler Tenant-Bezug – viele Events werden aber einen Tenant haben
    tenant_id: Optional[UUID] = None

    # Freies Metadaten-Feld (Tracing, Source-System, Correlation-Id etc.)
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def event_name(self) -> str:
        """
        Log-/Monitoring-freundlicher Name des Events.

        Standard: Klassenname (z. B. "CompanyUpdatedEvent").
        """
        return self.__class__.__name__

    def to_dict(self) -> Dict[str, Any]:
        """
        Einfache Serialisierung für Logging / Debugging.
        Subklassen können diese Methode überschreiben oder super() erweitern.
        """
        return {
            "id": str(self.id),
            "occurred_at": self.occurred_at.isoformat(),
            "tenant_id": str(self.tenant_id) if self.tenant_id else None,
            "event_name": self.event_name,
            "metadata": self.metadata,
        }
