# LeadLane Integration API – Developer Onboarding Guide

> **Audience:** Backend engineers taking over or extending the LeadLane Integration API  
> **Goal:** Give you enough context to understand the architecture, run the app locally, and safely extend it (especially CRM integrations and sync logic).

---

## Table of Contents

1. [What This Project Does](#what-this-project-does)
2. [High-Level Architecture](#high-level-architecture)
3. [Technology Stack & Conventions](#technology-stack--conventions)
4. [Local Development Setup](#local-development-setup)
5. [Configuration & Environment Variables](#configuration--environment-variables)
6. [Code Structure](#code-structure)
    - [Entry Point & Application Lifecycle](#entry-point--application-lifecycle)
    - [Database Layer](#database-layer)
    - [Domain Layer (UDM)](#domain-layer-udm)
    - [Events & Event Bus](#events--event-bus)
    - [Integrations Layer](#integrations-layer)
    - [Security & Authentication](#security--authentication)
    - [Error Handling](#error-handling)
7. [Data Flows & Examples](#data-flows--examples)
    - [LeadLane → CRM (Company Updated)](#flow-1-leadlane--crm-company-updated)
    - [CRM → LeadLane (Webhook)](#flow-2-crm--leadlane-webhook)
8. [Extending the System](#extending-the-system)
    - [Adding a New CRM System](#adding-a-new-crm-system)
    - [Adding New Mapped Fields](#adding-new-mapped-fields)
    - [Adding a New Entity Type](#adding-a-new-entity-type)
9. [Testing & Quality](#testing--quality)
10. [Troubleshooting & Debugging](#troubleshooting--debugging)
11. [Glossary](#glossary)

---

## What This Project Does

The **LeadLane Integration API** is an internal service that synchronizes LeadLane data (companies, contacts, opportunities, etc.) with external CRM systems such as:

- **HubSpot** (primary implementation)
- **Salesforce** (scaffolded)
- **SAP Business One** (scaffolded)
- **Pipedrive** (planned/scaffolded)

Core ideas:

- LeadLane has its own **data model** (multiple internal tables per tenant).
- The Integration API defines a **Unified Data Model (UDM)** that aggregates this data into rich domain objects (`Company`, `Contact`, `Opportunity`).
- A **mapping engine** converts UDM objects into CRM-specific payloads.
- A **sync layer** pushes changes to CRMs and ingests CRM webhooks back into LeadLane.
- Everything is designed to be **tenant-aware** and **multi-CRM capable**, but today the **HubSpot path is the most complete**.

---

## High-Level Architecture

Conceptually, the system is split into the following layers:

1. **API Layer (FastAPI)**
   - Exposes HTTP endpoints for:
     - Tenant CRM configuration (OAuth flows, status, disconnect)
     - Field mapping management
     - CRM webhooks
   - Handles authentication and validation.

2. **Domain Layer**
   - Unified Data Model (UDM) classes (`Company`, `Contact`, `Opportunity`).
   - Repositories that fetch data from the LeadLane database and build UDM objects.
   - Domain services and **domain events** (e.g. `CompanyUpdatedEvent`).

3. **Event Bus**
   - Internal, async event bus.
   - Decouples domain events from integration logic.

4. **Integrations Layer**
   - CRM clients (HubSpot, Salesforce, SAP B1, Pipedrive).
   - Field mapping engine (UDM ↔ CRM).
   - Sync listeners and handlers that react to events.
   - Webhook processors.

5. **Infrastructure Layer**
   - Configuration, environment, database connector, security (JWT).

You can think of the runtime dependency direction as:

```text
FastAPI API Layer
        ↓
   Domain Layer
        ↓
    Event Bus
        ↓
 Integrations Layer
        ↓
External CRMs (HubSpot, Salesforce, SAP B1, Pipedrive)
```

---

## Technology Stack & Conventions

- **Language:** Python 3.10+
- **Framework:** FastAPI (async, type-hinted)
- **Database:** PostgreSQL, accessed via **asyncpg**
- **Auth:** JWT (RS256) with public-key verification
- **HTTP Client:** httpx (async)
- **Config Management:** Pydantic `BaseSettings`
- **Style / Patterns:**
  - Clear separation of concerns by folder:
    - `config`, `db`, `domain`, `integrations`, `security`, `api`
  - Use of `dataclasses` for UDM models.
  - Use of Pydantic models for request/response DTOs and config.

---

## Local Development Setup

### 1. Prerequisites

- Python **3.10+**
- PostgreSQL (local or via Docker)
- A virtual environment (recommended)
- A valid JWT public key and correct issuer/audience (or a stub token in local dev)
- Optionally: sandbox accounts for CRMs (especially **HubSpot**)

### 2. Clone the Project

```bash
git clone <REPO_URL>
cd API
```

*(Replace `<REPO_URL>` with the actual repository URL.)*

### 3. Create and Activate a Virtual Environment

```bash
python -m venv .venv
source .venv/bin/activate    # on macOS / Linux
# .venv\Scriptsctivate.bat  # on Windows
```

### 4. Install Dependencies

```bash
pip install -r requirements.txt
```

If you’re using Poetry:

```bash
poetry install
poetry shell
```

### 5. Configure Environment Variables

Create a `.env` file in the project root (or configure your environment variables in your IDE).  
Use `app/config/settings.py` as the source of truth for what’s available.

Example (minimal) local configuration:

```env
# General
PROJECT_NAME="LeadLane Integration API"
API_V1_STR="/api/v1"
ENVIRONMENT="local"
DEBUG=true

# Database
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_DB=leadlane

# Auth (example values – replace with real ones)
JWT_PUBLIC_KEY="-----BEGIN PUBLIC KEY-----
...
-----END PUBLIC KEY-----"
JWT_ALGORITHM="RS256"
JWT_ISSUER="https://auth.leadlane.local/"
JWT_AUDIENCE="leadlane-api"

# CORS
BACKEND_CORS_ORIGINS=["http://localhost:3000"]

# CRM-specific variables may exist (check settings.py for the final list)
```

### 6. Database

You need a PostgreSQL instance with the LeadLane schema and integration tables. This repo currently does **not** include full migration scripts.

Typical options:

- Get a **schema dump** from another environment (e.g. staging).
- Use an existing local database prepared by the Data/Platform team.
- If there is a `schema.sql` or migration tool in another repo, follow those instructions.

The repository uses a custom `Database` wrapper over `asyncpg`, so once `POSTGRES_*` are set correctly, the app should be able to connect.

### 7. Run the Application

From the `API` directory:

```bash
uvicorn app.main:app --reload
```

By default, FastAPI will boot on `http://localhost:8000`.

Useful URLs:

- OpenAPI / Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`
- Root health/info endpoint: `http://localhost:8000/`

If the app starts successfully, you should see the project name and docs URLs returned from the root endpoint.

---

## Configuration & Environment Variables

Configuration is managed by `app/config/settings.py` using Pydantic’s `BaseSettings`.

Key concepts:

- All settings can come from environment variables, `.env` file, or defaults.
- A `Settings` instance is created once and cached (via `@lru_cache` for `get_settings()`).
- The `settings` object is imported across the codebase where needed.

Typical categories of settings:

1. **App / API Settings**
   - `PROJECT_NAME`
   - `API_V1_STR` (e.g. `/api/v1`)
   - `ENVIRONMENT` (e.g. `local`, `dev`, `staging`, `prod`)
   - `DEBUG`

2. **Database Settings**
   - `POSTGRES_HOST`
   - `POSTGRES_PORT`
   - `POSTGRES_USER`
   - `POSTGRES_PASSWORD`
   - `POSTGRES_DB`
   - Derived `DATABASE_URL` (e.g. `postgresql://user:pass@host:port/db`)

3. **Authentication / JWT**
   - `JWT_PUBLIC_KEY`
   - `JWT_ALGORITHM`
   - `JWT_ISSUER`
   - `JWT_AUDIENCE`

4. **CORS**
   - `BACKEND_CORS_ORIGINS` (list of string URLs)

5. **CRM-specific**
   - Secrets or config values for webhook validation, OAuth client IDs/secrets, etc.
   - Check `settings.py` and the `integrations` submodules for what’s required.

> **Tip:** When onboarding, it’s worth printing out `settings.dict()` in a local dev run (with secrets redacted) to confirm all expected values are set.

---

## Code Structure

### Entry Point & Application Lifecycle

- **File:** `app/main.py`
- **Key function:** `create_app()`

Responsibilities:

1. **Create FastAPI app instance**  
   - Configure title, docs URLs, version.

2. **Register middleware**  
   - CORS (based on `settings.BACKEND_CORS_ORIGINS`).

3. **Register exception handlers**  
   - From `app/api/error_handlers.py`.

4. **Initialize core infrastructure in the lifespan context**  
   - Create and connect the `Database` instance.
   - Initialize repositories and services.
   - Set up the `EventBus`.
   - Register event handlers (e.g. `CompanyUpdatedEvent` → CRM sync handler).

5. **Register routers**  
   - `app/api/router.py` under `settings.API_V1_STR`.

6. **Add root endpoint** (for a quick sanity check).

At the bottom of `main.py`:

```python
app = create_app()
```

This is what `uvicorn` imports.

---

### Database Layer

**File:** `app/db/database.py`

The `Database` class is a lightweight wrapper around `asyncpg` that provides:

- A connection pool (`asyncpg.create_pool`).
- Utility methods:
  - `connect()` / `disconnect()`:
    - Start/close the connection pool (called on startup/shutdown).
  - `fetch_one(query, params)`:
    - Returns a single row as a `Mapping` or `None`.
  - `fetch_all(query, params)`:
    - Returns multiple rows as a list of mappings.
  - `execute(query, params)`:
    - For `INSERT/UPDATE/DELETE`.
  - `execute_many(query, params_seq)`:
    - For batch operations.

#### Named Parameter Handling

The class supports **named parameters** in the SQL query, e.g.:

```sql
SELECT * FROM companies WHERE tenant_id = :tenant_id AND id = :company_id
```

Internally it:

1. Uses a regex to find `:param_name` placeholders.
2. Converts them to `$1`, `$2`, … for asyncpg.
3. Builds a list of values in the order of occurrence.

This allows repositories to use readable named params while still leveraging asyncpg’s positional binding.

---

### Domain Layer (UDM)

**Folder:** `app/domain`

#### Models

**Folder:** `app/domain/models`

Main dataclasses:

- `Company`
- `Contact`
- `Opportunity`

These classes:

- Represent **aggregated business entities**, not just single DB rows.
- Combine fields from multiple underlying tables (e.g. `central_database_sub_company`, tenant-specific tables).
- Include business-relevant fields like:
  - Names, domains, industries
  - Address & geodata
  - Financial metrics (`sales_eur`, `employees_total`, etc.)
  - LeadLane-specific fields (scores, tags, GPT summaries, etc.)

They are used as **canonical in-memory representations** for mapping and synchronization.

#### Repositories

**Folder:** `app/domain/repositories`

Example: `company_repository.py`

Responsibilities:

- Translate queries into one or more SQL statements using `Database`.
- Join multiple tables.
- Map query results into UDM objects (`Company`).

Typical method patterns:

- `get_by_id(tenant_id, sub_company_id) -> Optional[Company]`
- `list_for_tenant(tenant_id, filters) -> List[Company]`
- `_row_to_company(row, tenant_id) -> Company` (private helper)

#### Services

**Folder:** `app/domain/services`

Services encapsulate **business use cases**.

Examples (conceptually):

- Upserting a company and emitting events.
- Applying domain logic when certain fields change.
- Triggering the event bus when something important happens.

In this integration service, services often **bridge between repositories and the event bus**.

---

### Events & Event Bus

**Folder:** `app/domain/events`

Key components:

- `DomainEvent` (base class)
  - Contains common event metadata (e.g. `event_id`, `event_name`, `occurred_at`, etc.).
- `CompanyUpdatedEvent`
  - Extends `DomainEvent`.
  - Important fields:
    - `tenant_id: UUID`
    - `leadlane_sub_company_id: UUID`
    - `metadata: Dict[str, Any]` (optional extra info).

- `event_bus.py`
  - Implements a simple async event bus:
    - `subscribe(event_type, handler)`
    - `unsubscribe(event_type, handler)`
    - `publish(event)` (awaits all handlers)
    - Possibly `publish_background(event)` (schedule as async task)

Handlers are async callables taking a `DomainEvent` (or subclass).

This is the key mechanism that triggers CRM sync when something in the domain changes.

---

### Integrations Layer

**Folder:** `app/integrations`

This is where all CRM-specific logic lives.

#### CRM Types & Payloads

**File:** `app/integrations/crm_types.py`

- `CRMSystem` (Enum)
  - e.g. `hubspot`, `salesforce`, `sap_b1`, `pipedrive`.
- Pydantic payload models:
  - `CRMCompanyPayload`
  - `CRMContactPayload`
  - `CRMOpportunityPayload`
- `CRMSyncResult`
  - Standard envelope for CRM operations:
    - `success: bool`
    - `status_code: Optional[int]`
    - `error_code: Optional[str]`
    - `error_message: Optional[str]`
    - `raw_response: Optional[Dict[str, Any]]`

These payloads decouple UDM models from specific CRM client implementations.

#### Field Mapping

**Folder:** `app/integrations/mapping`

- `crm_field_mappings_repository.py`
  - Loads and stores **field mapping rules** from the DB.
  - Each mapping record typically binds:
    - UDM field name → CRM field identifier (e.g. `properties.name` for HubSpot).
- `crm_field_mapping_engine.py`
  - Core mapping logic.
  - Combines:
    - Default mappings (per CRM)
    - Tenant-specific overrides from the repository
  - Outputs:
    - `properties` dictionary for CRM payloads.
  - Handles `None` values carefully (usually skipping them instead of sending them as null, depending on the CRM behavior).

- Default mapping modules:
  - `hubspot_default_mapping.py`
  - `salesforce_default_mapping.py`
  - `sap_b1_default_mapping.py`
  - These set sensible defaults for each CRM; tenant-specific configs refine them.

#### CRM Clients

**Folder:** `app/integrations/crm`

Each CRM has (or will have) its own client module, e.g.:

- `hubspot_client.py`
- `salesforce_client.py`
- `sap_b1_client.py`
- `pipedrive_client.py`

Common patterns:

- Use `httpx.AsyncClient` for HTTP requests.
- Build URLs from CRM-specific base URLs and endpoints.
- Attach auth headers (e.g. `Authorization: Bearer <token>`).
- Implement methods like:
  - `upsert_company(payload: CRMCompanyPayload) -> CRMSyncResult`
  - `upsert_contact(...)`
  - `upsert_opportunity(...)`
- Catch HTTP errors and translate them into `CRMSyncResult` with useful context.

**Current state (important for you as a new dev):**

- **HubSpot** client is the most complete and should work end-to-end.
- **Salesforce** and **SAP B1** are mostly scaffolds and currently return “not implemented” results from their methods.
- **Pipedrive** may only exist in Enums/config and not yet as a real client.

#### Credentials Store

**Folder:** `app/integrations/credentials`

- `crm_credentials_store.py`
  - Central place to read/write **CRM credentials for a tenant**:
    - Access tokens
    - Refresh tokens
    - Expiration timestamps
    - Possibly instance URLs, scopes, etc.
  - Methods:
    - `get_connection_info(tenant_id, crm_system)`
    - `save_credentials(...)`
    - `disable_credentials(...)`

These credentials are used by CRM clients and verified by endpoints.

#### Sync Layer

**Folder:** `app/integrations/sync`

- `crm_sync_service.py`
- `crm_sync_listener.py`
- `handlers/company_crm_sync_handler.py`

Key idea:

- A **sync handler** subscribes to relevant domain events (e.g. `CompanyUpdatedEvent`).
- On event:
  1. Load the UDM object (e.g. `Company`) from the repository.
  2. Use the mapping engine to build the CRM payload.
  3. Execute one or more CRM client operations (depending on connected systems for the tenant).
  4. Log results (`CRMSyncResult`) for debugging/monitoring.

Example handler function:

```python
async def handle_company_updated(event: CompanyUpdatedEvent) -> None:
    company = await company_repository.get_by_id(
        tenant_id=event.tenant_id,
        sub_company_id=event.leadlane_sub_company_id,
    )
    if not company:
        # log and return
        return

    payload = CRMCompanyPayload(
        leadlane_sub_company_id=str(event.leadlane_sub_company_id),
        central_sub_company_id=getattr(company, "central_sub_company_id", None),
        # ...
        properties={},
    )

    await crm_sync_listener.sync_company(event.tenant_id, payload)
```

#### Webhooks

**Folder:** `app/integrations/webhooks`

- `webhook_security.py`
  - Functions to validate webhook signatures (e.g. HMAC).
- `webhook_idempotency_repository.py`
  - Stores processed webhook event IDs.
  - Prevents double-processing of the same event.
- CRM-specific processors, e.g.:
  - `hubspot_company_webhook_processor.py`
    - Knows how to interpret HubSpot’s webhook payloads.
    - Resolves HubSpot object IDs → LeadLane company relationships.
    - Triggers appropriate domain updates and/or events.

---

### Security & Authentication

**Folder:** `app/security`

Main file: `auth.py` (name may differ but is conceptually similar).

Responsibilities:

- Parse and validate `Authorization: Bearer <JWT>` header.
- Use `PyJWT` (or similar) to:
  - Verify signature against `settings.JWT_PUBLIC_KEY`.
  - Validate issuer (`JWT_ISSUER`) and audience (`JWT_AUDIENCE`).
  - Check expiration, etc.
- Extract:
  - `sub` (subject / user ID)
  - `tenant_id`
  - `scopes` (permissions)

Provides FastAPI dependencies such as:

- `get_current_token`
- `get_current_tenant_id_from_token`
- `ensure_path_tenant_matches_token`

These are used to secure endpoints and enforce that:

- A token can only act on its own `tenant_id`.
- Certain routes are restricted to admins (via scopes).

---

### Error Handling

**Folder:** `app/api/error_handlers.py`

Defines and registers custom exception handlers:

- For `HTTPException`:
  - Return a standard JSON error format (e.g. `{ "error": { "code": "...", "message": "..." } }`).
- For `RequestValidationError`:
  - Provide human-readable validation errors.
- For uncaught exceptions:
  - Return a generic `500` error (with minimal detail in production).
  - Possibly log stack traces (implementation detail).

This ensures a consistent error shape for frontend and other services.

---

## Data Flows & Examples

### Flow 1: LeadLane → CRM (Company Updated)

**Scenario:** A company is updated in LeadLane and needs to be synced to HubSpot.

1. **LeadLane Core updates data**  
   Somewhere outside this integration service, a company is modified.

2. **Domain Event Emitted**  
   - Code (in domain service) emits a `CompanyUpdatedEvent`:
     - Contains `tenant_id`
     - Contains `leadlane_sub_company_id`

3. **Event Bus Receives and Dispatches**  
   - `event_bus.publish(event)` is called.
   - All handlers registered for `CompanyUpdatedEvent` are invoked, including:
     - `company_crm_sync_handler.handle_company_updated`.

4. **Handler Loads UDM Company**  
   - Uses `CompanyRepository` and `Database` to fetch unified data.

5. **Payload Construction**  
   - Handler builds a `CRMCompanyPayload` from the UDM `Company`.
   - Field mapping engine may also be involved to construct `properties`.

6. **CRM Sync Listener**  
   - `CRMSyncListener` takes the payload and:
     - For each CRM connected for that tenant:
       - Invokes the appropriate client’s `upsert_company(...)`.

7. **CRM Client Call**  
   - HubSpot client performs HTTP request.
   - Response is parsed into `CRMSyncResult`.

8. **Result Handling**  
   - Success: do nothing or log.
   - Failure:
     - Log details.
     - Future enhancement: push into a retry queue or error store.

---

### Flow 2: CRM → LeadLane (Webhook)

**Scenario:** HubSpot sends a webhook indicating that a Company was changed on their side.

1. **HubSpot Sends Webhook**  
   - HTTP POST to a configured endpoint, for example:
     - `/api/v1/crm/hubspot/companies/webhook`

2. **Webhook Router Receives Request**  
   - Endpoint is defined in `crm_webhook_router`.
   - Parses path parameter `crm_system = "hubspot"`.

3. **Security Validation**  
   - Reads signature header (e.g. `X-HubSpot-Signature`).
   - Calls `verify_webhook_signature(...)`.
   - If invalid: return `401` or `403`.

4. **Idempotency Check**  
   - Event IDs are extracted from body.
   - `WebhookIdempotencyRepository` checks if they’ve been processed already.
   - If so, the event is skipped.

5. **Processor Logic**  
   - For HubSpot: `hubspot_company_webhook_processor.handle_events(events)`.
   - For each event:
     - Extract HubSpot company ID (`objectId`).
     - Resolve mapping to LeadLane company using a link table.
     - Optionally fetch latest company data from HubSpot using CRM client.
     - Map the data to UDM using `CRMFieldMappingEngine`.
     - Update the LeadLane DB via domain services.
     - Optionally emit a `CompanyUpdatedEvent` again if we want to fan out changes.

6. **Response**  
   - JSON with status and processed event count.

---

## Extending the System

### Adding a New CRM System

High-level steps (for example: Pipedrive):

1. **Extend `CRMSystem` enum** if not already present.
2. **Create a client implementation** under `app/integrations/crm/pipedrive_client.py`.
   - Implement:
     - Authentication (API token / OAuth).
     - `upsert_company`, `upsert_contact`, `upsert_opportunity`, etc.
3. **Add default field mappings** for Pipedrive.
4. **Update the field mapping engine** to handle the new CRM.
5. **Extend the credentials store** to support storing Pipedrive credentials.
6. **Add webhook endpoints & processors** under `integrations/webhooks` (if Pipedrive supports webhooks).
7. **Wire into the sync layer**:
   - Ensure `CRMSyncListener` knows to call the Pipedrive client when the tenant has Pipedrive enabled.

### Adding New Mapped Fields

1. Update the **UDM models** (`Company`, `Contact`, etc.) if the field doesn’t exist yet.
2. Update SQL in the **repository** to fetch the new field from DB.
3. Add a default mapping for each CRM in the appropriate `*_default_mapping.py`.
4. Expose the new mapping in the **field mapping DB table** if tenant-specific override is allowed.
5. Ensure the CRM supports the field and that the client sends it in payloads.

### Adding a New Entity Type

1. Create a new UDM dataclass (e.g. `Activity`, `Note`).
2. Add a repository for that entity.
3. Add domain events (`ActivityCreatedEvent`, etc.).
4. Implement handlers & sync logic in the integrations layer.
5. Extend CRM clients & mappings accordingly.

---

## Testing & Quality

At the moment, there may be **few or no tests** in the repo. For a production-ready integration layer, adding tests is highly recommended.

Suggested test coverage:

1. **Unit Tests**
   - Field mapping engine:
     - For each CRM, test a set of example UDM → CRM mappings.
   - CRM clients:
     - Mock HTTP calls with httpx’s mocking utilities.
     - Verify correct URLs, method, headers, and error handling.
   - Sync handlers:
     - Test that events lead to expected CRM client calls.

2. **Integration Tests**
   - Use a real test database.
   - Seed data and verify:
     - Repositories build correct UDM objects.
     - Webhook endpoints perform correct updates.

3. **End-to-End (Optional)**
   - With a sandbox HubSpot instance:
     - Trigger updates in LeadLane → verify CRM updated.
     - Trigger changes in HubSpot → verify LeadLane updated.

Suggested tools / commands (once tests exist):

```bash
pytest
```

You can configure a `pytest.ini` to handle test DB settings and environment loading.

---

## Troubleshooting & Debugging

### Common Issues

1. **App won’t start – DB connection error**
   - Check `POSTGRES_HOST`, `POSTGRES_PORT`, `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`.
   - Make sure PostgreSQL is running and accessible.

2. **401 / 403 Errors on API**
   - Check that you pass a valid JWT in `Authorization: Bearer <token>`.
   - In local dev, you might use a simplified token or disable strict key verification temporarily (only locally).

3. **CRM Sync Not Happening**
   - Check logs for event emission (e.g. `CompanyUpdatedEvent`).
   - Verify that the sync handler is subscribed to the event bus.
   - Confirm that the tenant actually has credentials stored for the CRM.
   - Inspect `CRMSyncResult` for error codes and messages.

4. **Webhook Not Being Processed**
   - Confirm the CRM is calling the correct URL and that it’s accessible.
   - Check signature validation (shared secrets, keys).
   - Look at the idempotency repository to see if events were considered duplicates.

5. **Field Mapping Issues**
   - Compare UDM fields and CRM fields.
   - Check DB-stored mappings for the tenant.
   - Temporarily log the constructed payload before sending to the CRM.

---

## Glossary

- **UDM (Unified Data Model):**  
  Internal representation of business entities (Company, Contact, Opportunity) that aggregates data from various internal tables.

- **Domain Event:**  
  A message emitted when something meaningful happens in the domain (e.g. a company is updated). Used to decouple the cause of a change from its effects.

- **Event Bus:**  
  Internal system responsible for dispatching domain events to all interested handlers.

- **CRM Client:**  
  A Python class wrapping the HTTP API of a CRM (HubSpot, Salesforce, etc.), translating generic payloads into concrete API calls.

- **Field Mapping Engine:**  
  Component that maps UDM fields to CRM fields using default and tenant-specific configurations.

- **Tenant:**  
  A logical customer/account in LeadLane. Each tenant may connect to one or multiple CRMs.

- **Webhook:**  
  HTTP callback sent by external systems (e.g. HubSpot) to notify us about changes on their side.

---

If you are new to this codebase, a good **first week plan** would be:

1. Get the app running locally with a test database.
2. Explore the UDM models and repositories for `Company`.
3. Trace the **CompanyUpdatedEvent** flow end-to-end.
4. Inspect how the HubSpot client is implemented and how payloads are built.
5. Add or fix a small piece of mapping or sync logic and ship it behind a feature flag or to a test tenant.
