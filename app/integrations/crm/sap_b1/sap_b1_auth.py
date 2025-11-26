# app/integrations/crm/sap_b1/sap_b1_auth.py
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Mapping, Optional, Any, Dict


class SAPB1AuthError(RuntimeError):
    """
    Fehler rund um Authentifizierung / Session für SAP Business One.
    """
    pass


@dataclass
class SAPB1Credentials:
    """
    Typisierte Repräsentation der SAP Business One (Service Layer) Credentials.

    Typischer Service-Layer-Flow:
      - base_url: z.B. https://sap-server:50000
      - company_db: Name der Company-DB
      - session_id: ggf. bereits bestehende Session (B1SESSION)
      - expires_at: optionales Ablaufdatum der Session
      - username / password: optional, falls Session-Handling hier
        oder an anderer Stelle stattfinden soll.
    """

    base_url: Optional[str] = None
    company_db: Optional[str] = None

    session_id: Optional[str] = None
    expires_at: Optional[datetime] = None

    username: Optional[str] = None
    password: Optional[str] = None

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any]) -> "SAPB1Credentials":
        """
        Baut Credentials aus einem generischen Mapping (z.B. DB-Zeile).
        Erwartete Keys:
          - base_url
          - company_db
          - session_id
          - expires_at (ISO/Timestamp/datetime)
          - username
          - password
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
            base_url=data.get("base_url"),
            company_db=data.get("company_db"),
            session_id=data.get("session_id"),
            expires_at=expires_at,
            username=data.get("username"),
            password=data.get("password"),
        )

    def is_expired(self, skew_seconds: int = 60) -> bool:
        """
        Prüft, ob die Session abgelaufen ist – mit etwas Zeitpuffer.
        Wenn kein expires_at gesetzt ist, gehen wir von "nicht abgelaufen" aus.
        """
        if not self.expires_at:
            return False

        now = datetime.now(timezone.utc)
        skew = timedelta(seconds=skew_seconds)
        return now + skew >= self.expires_at

    def require_valid_for_request(self) -> None:
        """
        Wirft einen Fehler, wenn wir keine sinnvolle Basis für Requests haben.
        Mindestens base_url + company_db + session_id müssen vorhanden sein.
        """
        if not self.base_url:
            raise SAPB1AuthError("SAP B1 base_url fehlt.")
        if not self.company_db:
            raise SAPB1AuthError("SAP B1 company_db fehlt.")
        if not self.session_id:
            # In einem späteren Schritt könnte man hier automatisch ein Login machen
            raise SAPB1AuthError("SAP B1 Session (session_id) fehlt.")

    def build_headers(
        self,
        extra: Optional[Mapping[str, str]] = None,
    ) -> Dict[str, str]:
        """
        Baut HTTP-Header für einen Request an die SAP B1 Service Layer API.
        """
        self.require_valid_for_request()

        headers: Dict[str, str] = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            # Service Layer nutzt B1SESSION Cookie
            "Cookie": f"B1SESSION={self.session_id}; CompanyDB={self.company_db}",
        }

        if extra:
            headers.update(extra)

        return headers
