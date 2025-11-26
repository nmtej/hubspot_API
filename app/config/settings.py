from __future__ import annotations

from enum import Enum
from functools import lru_cache
from typing import List, Optional

from pydantic import AnyHttpUrl, BaseSettings, validator


class AppEnvironment(str, Enum):
    LOCAL = "local"
    DEV = "dev"
    STAGING = "staging"
    PROD = "prod"


class Settings(BaseSettings):
    """
    Zentrale Application-Settings.
    """

    # ------------------------------------------------------------------ #
    # Basis-Infos
    # ------------------------------------------------------------------ #

    app_name: str = "LeadLane API"
    app_version: str = "0.1.0"

    environment: AppEnvironment = AppEnvironment.LOCAL
    debug: bool = True

    api_prefix: str = "/api"

    # ------------------------------------------------------------------ #
    # Datenbank / Persistence
    # ------------------------------------------------------------------ #

    database_url: str
    database_schema: str = "public"

    # ------------------------------------------------------------------ #
    # Security / Auth
    # ------------------------------------------------------------------ #

    secret_key: str = "CHANGE_ME_IN_PRODUCTION"
    access_token_expire_minutes: int = 60 * 24  # 24h

    # **JWT für API-Auth**
    jwt_issuer: str = "https://auth.leadlane.local"   # z.B. OIDC-Issuer
    jwt_audience: str = "leadlane-api"
    # bei HS256: shared secret, bei RS256: Public Key (PEM)
    jwt_public_key: str = ""
    jwt_algorithm: str = "RS256"  # oder "HS256"

    # ------------------------------------------------------------------ #
    # CORS
    # ------------------------------------------------------------------ #

    cors_origins: List[AnyHttpUrl] = []

    @validator("cors_origins", pre=True)
    def parse_cors_origins(cls, v):  # type: ignore[override]
        if isinstance(v, str):
            origins = [origin.strip() for origin in v.split(",") if origin.strip()]
            return origins
        if isinstance(v, list):
            return v
        return []

    # ------------------------------------------------------------------ #
    # CRM / Integrations (global, nicht tenant-spezifisch)
    # ------------------------------------------------------------------ #

    enable_hubspot: bool = True
    enable_salesforce: bool = True
    enable_sap_b1: bool = True
    enable_pipedrive: bool = False

    hubspot_base_url: str = "https://api.hubapi.com"
    salesforce_api_version: str = "v58.0"
    sap_b1_service_layer_url: Optional[str] = None

    # ------------------------------------------------------------------ #
    # HubSpot OAuth Config (global, vom Anbieter)
    # ------------------------------------------------------------------ #

    hubspot_client_id: str
    hubspot_client_secret: str
    hubspot_redirect_uri: AnyHttpUrl
    hubspot_scopes: str = "crm.objects.contacts.read crm.objects.contacts.write"
    hubspot_webhook_secret: Optional[str] = None

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True

        fields = {
            "database_url": {"env": "DATABASE_URL"},
            "environment": {"env": "APP_ENV"},
            "secret_key": {"env": "SECRET_KEY"},
            "cors_origins": {"env": "CORS_ORIGINS"},

            "hubspot_client_id": {"env": "HUBSPOT_CLIENT_ID"},
            "hubspot_client_secret": {"env": "HUBSPOT_CLIENT_SECRET"},
            "hubspot_redirect_uri": {"env": "HUBSPOT_REDIRECT_URI"},
            "hubspot_scopes": {"env": "HUBSPOT_SCOPES"},
            "hubspot_webhook_secret": {"env": "HUBSPOT_WEBHOOK_SECRET"},
            # JWT kannst du entweder per Default-Namen setzen oder hier mappen:
            # "jwt_issuer": {"env": "JWT_ISSUER"},
            # "jwt_audience": {"env": "JWT_AUDIENCE"},
            # "jwt_public_key": {"env": "JWT_PUBLIC_KEY"},
            # "jwt_algorithm": {"env": "JWT_ALGORITHM"},
        }


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings: Settings = get_settings()
