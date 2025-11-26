# app/integrations/webhooks/webhook_security.py
from __future__ import annotations

import base64
import hashlib
import hmac
import time
from typing import Mapping, Optional

from fastapi import HTTPException, status

from app.config import settings
from app.integrations.crm.crm_types import CRMSystem


def _safe_compare(a: str, b: str) -> bool:
    """
    Konstante Zeitvergleichs-Funktion zum Schutz vor Timing-Angriffen.
    """
    return hmac.compare_digest(a, b)


def _require_hubspot_secret() -> str:
    secret = settings.hubspot_webhook_secret
    if not secret:
        # Wenn kein Secret konfiguriert ist, lieber failen
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="HubSpot webhook secret not configured",
        )
    return secret


def _validate_hubspot_v1(*, secret: str, raw_body: bytes, signature: str) -> None:
    """
    v1-Signatur (CRM-Object Webhooks):

      expected = SHA256( client_secret + request_body )

    Siehe HubSpot-Doku:
      - v1: Client secret + request body → SHA256, hex 
    """
    body_str = raw_body.decode("utf-8")
    source = f"{secret}{body_str}"
    expected = hashlib.sha256(source.encode("utf-8")).hexdigest()
    if not _safe_compare(expected, signature):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid HubSpot v1 webhook signature",
        )


def _validate_hubspot_v2(
    *,
    secret: str,
    method: str,
    request_uri: str,
    raw_body: bytes,
    signature: str,
) -> None:
    """
    v2-Signatur (Workflow-Webhooks / CRM-Cards):

      expected = SHA256( client_secret + http_method + URI + request_body )
      
    """
    body_str = raw_body.decode("utf-8")
    source = f"{secret}{method.upper()}{request_uri}{body_str}"
    expected = hashlib.sha256(source.encode("utf-8")).hexdigest()
    if not _safe_compare(expected, signature):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid HubSpot v2 webhook signature",
        )


def _validate_hubspot_v3(
    *,
    secret: str,
    method: str,
    request_uri: str,
    raw_body: bytes,
    headers: Mapping[str, str],
) -> None:
    """
    v3-Signatur (empfohlene aktuelle Variante):

    - Header:
        X-HubSpot-Signature-V3
        X-HubSpot-Request-Timestamp
    - expected = Base64( HMAC_SHA256( app_secret, method + uri + body + timestamp ) )
    - timestamp ist Epoch-Millis; Request >5 Minuten alt wird rejected. 
    """
    signature = headers.get("X-HubSpot-Signature-v3") or headers.get(
        "X-HubSpot-Signature-V3"
    )
    if not signature:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing HubSpot v3 signature header",
        )

    ts_header = headers.get("X-HubSpot-Request-Timestamp")
    if not ts_header:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing HubSpot timestamp header",
        )

    try:
        ts_ms = int(ts_header)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid HubSpot timestamp header",
        )

    # Replay-Schutz: maximal ±5 Minuten
    now_ms = int(time.time() * 1000)
    five_min_ms = 5 * 60 * 1000
    if abs(now_ms - ts_ms) > five_min_ms:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="HubSpot webhook timestamp too old",
        )

    body_str = raw_body.decode("utf-8")
    source = f"{method.upper()}{request_uri}{body_str}{ts_header}"

    mac = hmac.new(
        secret.encode("utf-8"),
        msg=source.encode("utf-8"),
        digestmod=hashlib.sha256,
    )
    expected_bytes = mac.digest()
    expected_b64 = base64.b64encode(expected_bytes).decode("utf-8")

    if not _safe_compare(expected_b64, signature):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid HubSpot v3 webhook signature",
        )


def verify_webhook_signature(
    *,
    crm_system: CRMSystem,
    headers: Mapping[str, str],
    raw_body: bytes,
    method: Optional[str] = None,
    request_uri: Optional[str] = None,
) -> None:
    """
    Wirft HTTPException(401), wenn die Signatur nicht passt.

    Für HubSpot werden v1, v2 und v3 unterstützt:
      - v3, wenn X-HubSpot-Signature-Version == "v3"
      - v2, wenn Version "v2"
      - sonst v1 (Standard für CRM-Object-Webhooks)
    """
    if crm_system == CRMSystem.HUBSPOT:
        secret = _require_hubspot_secret()

        version = headers.get("X-HubSpot-Signature-Version", "").lower().strip()

        # v3 – empfohlen
        if version == "v3":
            if not method or not request_uri:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Missing method/URI for HubSpot v3 signature validation",
                )
            _validate_hubspot_v3(
                secret=secret,
                method=method,
                request_uri=request_uri,
                raw_body=raw_body,
                headers=headers,
            )
            return

        # v2 (Workflows / CRM-Cards)
        if version == "v2":
            if not method or not request_uri:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Missing method/URI for HubSpot v2 signature validation",
                )
            signature = headers.get("X-HubSpot-Signature", "")
            _validate_hubspot_v2(
                secret=secret,
                method=method,
                request_uri=request_uri,
                raw_body=raw_body,
                signature=signature,
            )
            return

        # Default / v1
        signature = headers.get("X-HubSpot-Signature", "")
        _validate_hubspot_v1(secret=secret, raw_body=raw_body, signature=signature)
        return

    # Weitere CRMs später ergänzen (Salesforce, SAP B1, Pipedrive)
    # Aktuell: keine Signaturprüfung für andere Systeme
    return
