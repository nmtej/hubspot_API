# app/integrations/crm/salesforce/salesforce_auth.py
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Mapping, Optional, Any, Dict


class SalesforceAuthError(RuntimeError):
    """
    Fehler rund um Authentifizierung / Tokens für Salesforce.
    """
    pass


@dataclass
class SalesforceCredentials:
    """
    Typisierte Repräsentation der Salesforce-Credentials.

    Erwartete Daten (typischer OAuth2-Flow):
      - access_token
      - refresh_token (optional)
      - instance_url (https://yourInstance.salesforce.com)
      - expires_at (optional; wenn nicht gesetzt, wird kein Ablauf geprüft)
    """

    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    instance_url: Optional[str] = None
    expires_at: Optional[datetime] = None

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any]) -> "SalesforceCredentials":
        """
        Baut SalesforceCredentials aus einem generischen Mapping, z.B. aus einer DB-Zeile.
        Erwartete Keys:
          - access_token
          - refresh_token
          - instance_url
          - expires_at (ISO-String, Timestamp oder datetime)
        """
        expires_at_raw = data.get("expires_at")
        expires_at: Optional[datetime] = None

        if isinstance(expires_at_raw, datetime):
            expires_at = expires_at_raw
        elif isinstance(expires_at_raw, (int, float)):
            expires_at = datetime.fromtimestamp(expires_at_raw, tz=timezone.utc)
        elif isinstance(expires_at_raw, str):
            try:
                expires_at = datetime.fromisoformat(expires_at_raw)
                if expires_at.tzinfo is None:
                    expires_at = expires_at.replace(tzinfo=timezone.utc)
            except ValueError:
                expires_at = None

        return cls(
            access_token=data.get("access_token"),
            refresh_token=data.get("refresh_token"),
            instance_url=data.get("instance_url"),
            expires_at=expires_at,
        )

    def is_expired(self, skew_seconds: int = 60) -> bool:
        """
        Prüft, ob das Access Token abgelaufen ist – mit etwas Zeitpuffer.
        Wenn kein expires_at gesetzt ist, gehen wir von "nicht abgelaufen" aus.
        """
        if not self.expires_at:
            return False

        now = datetime.now(timezone.utc)
        skew = timedelta(seconds=skew_seconds)
        return now + skew >= self.expires_at

    def require_valid_for_request(self) -> None:
        """
        Wirft einen Fehler, wenn wir keinen sinnvollen Auth-Status haben.
        """
        if not self.access_token:
            raise SalesforceAuthError("Salesforce access_token fehlt.")
        if not self.instance_url:
            raise SalesforceAuthError("Salesforce instance_url fehlt.")

    def build_headers(
        self,
        extra: Optional[Mapping[str, str]] = None,
    ) -> Dict[str, str]:
        """
        Baut HTTP-Header für einen Request an Salesforce.
        """
        self.require_valid_for_request()

        headers: Dict[str, str] = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

        if extra:
            headers.update(extra)

        return headers
