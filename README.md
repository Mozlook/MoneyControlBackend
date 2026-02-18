# MoneyControl Backend

MoneyControl is a personal finance backend API built with FastAPI. It supports multi-wallet budgeting, shared wallets (members/roles), catalog management (categories/products), transactions (including refunds and optional FX fields), recurring expenses with “apply” logic per billing period, dashboard aggregations, CSV export, and structured JSONL audit logging.

## Features

- **Google OAuth login** (backend verifies Google `id_token`) and issues its own **JWT** access token.
- **Multi-wallet** support: a user can own or join multiple wallets.
- **Wallet sharing**: owners can add members (editor role).
- **Catalog**: categories and products with soft-delete and hard-delete flows.
- **Transactions**:
  - create/list
  - refund (creates a linked refund transaction)
  - soft-delete with integrity rules
  - optional FX fields (original amount/currency + FX rate)
- **Recurring expenses**:
  - create/list/update
  - activate/deactivate
  - apply recurring items for a billing period (generates transactions)
- **Dashboard**:
  - categories/products totals
  - totals by product importance
  - history for last N billing periods
- **CSV export** of transactions.
- **Structured JSONL logs** with request tracing and audit event types (useful for SIEM ingestion).

## Tech stack

- **Python** 3.12
- **FastAPI** (ASGI)
- **SQLAlchemy** + **PostgreSQL**
- **Alembic** migrations
- **Docker / Docker Compose**
- Auth:
  - Google ID token verification
  - JWT issued by the backend

## Repository layout (high level)

Typical structure:

- `app/main.py` – FastAPI app, middleware, router registration
- `app/routers/` – HTTP routes (auth, wallets, categories, products, transactions, recurring, settings, summary, history)
- `app/handlers/` – business logic used by routers
- `app/models/` – SQLAlchemy ORM models
- `app/schemas/` – Pydantic request/response schemas
- `app/deps.py` – dependencies (DB session, current user)
- `app/logging_setup.py` – JSONL structured logging setup
- `alembic/` – migrations

## Configuration

MoneyControl is configured via environment variables (Docker Compose recommended).

### Core

- `DATABASE_URL`  
  SQLAlchemy connection string, e.g.:
  - `postgresql+psycopg2://moneycontrol:password@db:5432/moneycontrol`

- `JWT_SECRET`  
  Secret used to sign JWT tokens.

- `GOOGLE_CLIENT_ID`  
  Google OAuth client ID used to validate the `id_token` audience.

- `CORS_ORIGINS`  
  Comma-separated list of allowed frontend origins, e.g.:
  - `https://moneycontrol.example.com,https://staging-moneycontrol.example.com`

- `ROOT_PATH`  
  Optional. If the API is mounted behind a reverse proxy under a prefix (for example `/moneycontrol`), set:
  - `ROOT_PATH=/moneycontrol`

### Structured logging (JSONL)

- `APP_NAME` (default: `MoneyControl`)
- `LOG_PATH` (default recommended: `/logs/moneycontrol.jsonl`)
- `LOG_LEVEL` (default recommended: `INFO`)
- `LOG_INCLUDE_STACKTRACE` (optional; `1` to include stack traces on error logs)

Bind-mount a host directory into the container so the SIEM (or other tooling) can read logs from the host filesystem.

Example mapping:

- Host: `/srv/app_logs/MoneyControl`
- Container: `/logs`
- `LOG_PATH=/logs/moneycontrol.jsonl`

## Local development

### Prerequisites

- Docker + Docker Compose
- (Optional) Python 3.12 locally if you want to run without Docker

### Run with Docker Compose

1. Create an env file (example `.env.prod` or `.env`) with required variables:
   - `POSTGRES_PASSWORD`
   - `JWT_SECRET`
   - `GOOGLE_CLIENT_ID`
   - `CORS_ORIGINS`

2. Start database and backend:

```bash
docker compose -f docker-compose.prod.yml --env-file .env.prod up -d --build
```

3. Run migrations:

```bash
docker compose -f docker-compose.prod.yml --env-file .env.prod run --rm backend alembic upgrade head
```

4. Health check:

```bash
curl -fsS http://127.0.0.1:8010/health
```

### Run without Docker (optional)

If you run locally without Docker, ensure Postgres is available and `DATABASE_URL` points to it.

```bash
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

## API authentication

### 1) Obtain JWT via Google login

**POST** `/auth/google`

Request body:

```json
{
  "id_token": "GOOGLE_ID_TOKEN"
}
```

Response:

```json
{
  "access_token": "JWT_ACCESS_TOKEN",
  "token_type": "bearer"
}
```

### 2) Use the token

Include the access token on protected endpoints:

```
Authorization: Bearer <JWT_ACCESS_TOKEN>
```

## API reference (summary)

Internally (FastAPI routing) the endpoints are defined without that prefix.

### Auth

- `POST /auth/google`  
  Exchange a Google `id_token` for a backend JWT.

### Users

- `GET /users/me`  
  Return the current user.

### Wallets

- `GET /wallets`  
  List wallets where the current user is a member.

- `POST /wallets`  
  Create a wallet.

- `GET /wallets/{wallet_id}`  
  Get a wallet by id.

- `GET /wallets/{wallet_id}/members`  
  List wallet members.

- `POST /wallets/{wallet_id}/members`  
  Add a member to a wallet (owner-only).

### Categories

- `GET /wallets/{wallet_id}/categories`  
  List categories (optional `deleted=false`).

- `POST /wallets/{wallet_id}/categories`  
  Create category.

- `DELETE /wallets/{wallet_id}/categories/{category_id}`  
  Soft delete category.

- `DELETE /wallets/{wallet_id}/categories/{category_id}/hard`  
  Hard delete category (typically requires prior soft-delete and no references).

- `GET /wallets/{wallet_id}/categories/with-sum`  
  List categories with sums for a billing period or date range.

### Products

- `GET /wallets/{wallet_id}/products`  
  List products (filters: `category_id`, `deleted`).

- `POST /wallets/{wallet_id}/products`  
  Create product.

- `DELETE /wallets/{wallet_id}/products/{product_id}`  
  Soft delete product.

- `DELETE /wallets/{wallet_id}/products/{product_id}/hard`  
  Hard delete product.

- `GET /wallets/{wallet_id}/products/with-sum`  
  List products with sums for a billing period or date range.

### Transactions

- `GET /wallets/{wallet_id}/transactions`  
  List transactions with filters:
  - `from_date`, `to_date`
  - `current_period`
  - `category_id`, `product_id`

- `POST /wallets/{wallet_id}/transactions`  
  Create a transaction.

- `POST /wallets/{wallet_id}/transactions/{transaction_id}/refund`  
  Refund a transaction (creates a linked refund transaction).

- `DELETE /wallets/{wallet_id}/transactions/{transaction_id}`  
  Soft delete a transaction (blocked if it has refunds).

- `GET /wallets/{wallet_id}/transactions/export`  
  Export transactions (default `format=csv`).

### Recurring

- `GET /wallets/{wallet_id}/recurring`  
  List recurring items (`active=true/false` optional).

- `POST /wallets/{wallet_id}/recurring`  
  Create recurring item.

- `PUT /wallets/{wallet_id}/recurring/{recurring_id}`  
  Update recurring item.

- `DELETE /wallets/{wallet_id}/recurring/{recurring_id}`  
  Deactivate recurring item.

- `PUT /wallets/{wallet_id}/recurring/{recurring_id}/activate`  
  Activate recurring item.

- `POST /wallets/{wallet_id}/recurring/apply`  
  Apply recurring items for the current billing period (generates transactions).

### Settings

- `GET /settings`  
  Get current user settings.

- `PUT /settings`  
  Update current user settings (partial update).

### Summary

- `GET /wallets/{wallet_id}/summary/categories-products`  
  Categories/products summary for a billing period or date range.

- `GET /wallets/{wallet_id}/summary/by-importance`  
  Totals grouped by product importance for a billing period or date range.

### History

- `GET /wallets/{wallet_id}/history/last-periods?periods=6`  
  Totals for the last N billing periods.

### Health

- `GET /health`  
  Basic health check.

- `GET /db-check`  
  DB connectivity check.

## Structured logging and audit events

The backend writes **JSON Lines** (JSONL): one JSON object per line. This makes it easy to ship logs to a SIEM or ingest them with a file tailer.

### Typical fields

Depending on the event type, log entries can include:

- `ts` – timestamp (UTC ISO 8601)
- `level` – log level
- `app` – application name (`APP_NAME`)
- `host` – hostname/container id
- `message` – human-readable message
- `event_type` – machine-readable event identifier (important for SIEM)
- `request_id` – request correlation id
- `user_id` – authenticated user id (when available)
- `src_ip` – source IP (when available)
- `user_agent` – client user agent (when available)
- `method`, `path`, `status`, `latency_ms` – HTTP metadata (for `http_request`)
- `error_type` – exception class name (for error events)
- `data` – event-specific structured payload

### Event types (examples)

- HTTP tracing:
  - `http_request`
  - `unhandled_exception`

- Auth:
  - `auth_oauth_google_login_success`
  - `auth_oauth_google_login_failed`

- Authorization / access control:
  - `permission_denied`

- Audit events (selected):
  - `audit_wallet_created`
  - `audit_wallet_member_added`
  - `audit_category_created`
  - `audit_category_deleted_soft`
  - `audit_category_deleted_hard`
  - `audit_product_created`
  - `audit_product_deleted_soft`
  - `audit_product_deleted_hard`
  - `audit_transaction_created`
  - `audit_transaction_refunded`
  - `audit_transaction_deleted_soft`
  - `audit_transactions_exported`
  - `audit_recurring_created`
  - `audit_recurring_updated`
  - `audit_recurring_deactivated`
  - `audit_recurring_activated`
  - `audit_recurring_applied`
  - `audit_settings_updated`

## CORS

If your frontend runs on a different domain (for example Netlify) you must set `CORS_ORIGINS` to include the frontend origin(s). Use a comma-separated list.

Example:

```env
CORS_ORIGINS=https://moneycontrol.example.com
```

## Deployment notes

- The container listens on port `8000`. In production you will typically:
  - bind it to `127.0.0.1` on the VPS, and
  - expose it via a reverse proxy (nginx/Traefik/Caddy) with TLS.
- If you mount the API under a path prefix (e.g. `/moneycontrol`), configure the reverse proxy to **strip the prefix** and set `ROOT_PATH=/moneycontrol` so FastAPI generates correct OpenAPI/links.

## Troubleshooting

- **CORS errors in the browser**:
  - ensure `CORS_ORIGINS` contains the exact frontend origin
  - ensure the reverse proxy routes and preflight (OPTIONS) requests are forwarded correctly

- **404 under a prefixed path** (e.g. `/moneycontrol/...`):
  - confirm your reverse proxy strips the prefix before proxying to the backend
  - confirm `ROOT_PATH` matches the external prefix

- **No logs written**:
  - confirm `LOG_PATH` points to a writable directory inside the container
  - confirm the bind mount exists on the host and is writable

## Roadmap

See `app/backlog.md` for the MVP scope, completed items, and next milestones.
