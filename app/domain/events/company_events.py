# app/domain/events/company_events.py
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict , Optional
from uuid import UUID

from .domain_event import DomainEvent


@dataclass
class CompanyUpdatedEvent(DomainEvent):
    """
    Event, das gefeuert wird, wenn eine Company gespeichert/aktualisiert wurde.

    Wichtige Nutzdaten:
      - tenant_id
      - leadlane_sub_company_id (Domain-ID aus LeadLane)
    """

    tenant_id: UUID  # überschreibt das optionale Feld in DomainEvent zu "required"
    leadlane_sub_company_id: Optional[UUID] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
