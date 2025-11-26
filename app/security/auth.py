# app/security/auth.py


from typing import Optional, List
from uuid import UUID

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field

from app.config import settings

security_scheme = HTTPBearer(auto_error=False)


class AuthSettings(BaseModel):
    jwt_issuer: str
    jwt_audience: str
    jwt_public_key: str  # oder shared secret für HS256
    jwt_algorithm: str = "RS256"  # oder "HS256"


auth_settings = AuthSettings(
    jwt_issuer=settings.jwt_issuer,
    jwt_audience=settings.jwt_audience,
    jwt_public_key=settings.jwt_public_key,
    jwt_algorithm=settings.jwt_algorithm,
)


class TokenData(BaseModel):
    sub: str
    tenant_id: UUID
    scopes: List[str] = Field(default_factory=list)


def _decode_jwt(token: str) -> dict:
    try:
        payload = jwt.decode(
            token,
            auth_settings.jwt_public_key,
            algorithms=[auth_settings.jwt_algorithm],
            audience=auth_settings.jwt_audience,
            issuer=auth_settings.jwt_issuer,
        )
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="token_expired",
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid_token",
        )

    return payload


async def get_current_token(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_scheme),
) -> TokenData:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="missing_or_invalid_authorization_header",
        )

    payload = _decode_jwt(credentials.credentials)

    # erwartetes Token-Format:
    # {
    #   "sub": "user-or-client-id",
    #   "tenant_id": "f4e8e88a-....-....",
    #   "scope": "crm:read crm:write"
    #   ...
    # }
    try:
        tenant_id = UUID(payload["tenant_id"])
    except (KeyError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="tenant_id_missing_or_invalid_in_token",
        )

    scopes = payload.get("scope") or payload.get("scopes") or ""
    if isinstance(scopes, str):
        scopes = scopes.split()

    return TokenData(
        sub=str(payload.get("sub") or tenant_id),
        tenant_id=tenant_id,
        scopes=scopes,
    )
