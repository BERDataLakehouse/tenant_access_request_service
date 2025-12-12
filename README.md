# Tenant Access Request Service

[![Lint and Test](https://github.com/BERDataLakehouse/tenant_access_request_service/actions/workflows/test.yml/badge.svg)](https://github.com/BERDataLakehouse/tenant_access_request_service/actions/workflows/test.yml)
[![codecov](https://codecov.io/gh/BERDataLakehouse/tenant_access_request_service/graph/badge.svg)](https://codecov.io/gh/BERDataLakehouse/tenant_access_request_service)

A FastAPI service that provides a Slack-based approval workflow for tenant access requests, following the same architecture as `minio_manager_service`.

## Architecture

```
tenant_access_request_service/
├── src/
│   ├── main.py                # FastAPI app factory with middleware
│   ├── routes/
│   │   ├── health.py          # GET /health - no auth
│   │   ├── requests.py        # POST /requests - user endpoint (any authenticated user)
│   │   ├── approvals.py       # POST /approvals/approve|deny - admin endpoint
│   │   └── slack.py           # POST /slack/interact - Slack callback
│   ├── core/
│   │   ├── slack_client.py    # Slack message sending + signature verification
│   │   └── governance_client.py # Governance API client for minio_manager_service
│   └── service/
│       ├── config.py          # Settings from env vars
│       ├── app_state.py       # KBase auth + client initialization
│       ├── kb_auth.py         # KBase authentication
│       ├── dependencies.py    # auth + require_admin dependencies
│       └── ...                # exceptions, models, etc.
├── tests/                     # Unit tests
├── Dockerfile
├── pyproject.toml
└── uv.lock
```

## API Endpoints

### `GET /health`
Health check endpoint. No authentication required.

### `POST /requests` (User endpoint)
Submit a tenant access request. **Requires authenticated user**.

```json
{
  "tenant_name": "kbase",
  "permission": "read_only",
  "justification": "Need access for analysis"
}
```

### `POST /approvals/approve` (Admin endpoint)
Approve an access request. **Requires CDM_JUPYTERHUB_ADMIN role**.

```json
{
  "requester": "jdoe",
  "tenant_name": "kbase",
  "permission": "read_only"
}
```

### `POST /approvals/deny` (Admin endpoint)
Deny an access request. **Requires CDM_JUPYTERHUB_ADMIN role**.

### `POST /slack/interact`
Slack interactive callback. Called by Slack when users click buttons.

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `SLACK_BOT_TOKEN` | Yes | Slack Bot OAuth Token (xoxb-...) |
| `SLACK_SIGNING_SECRET` | Yes | Slack Signing Secret |
| `SLACK_CHANNEL_ID` | Yes | Channel ID for admin notifications |
| `GOVERNANCE_API_URL` | Yes | URL of minio_manager_service |
| `KBASE_AUTH_URL` | No | KBase Auth URL (default: ci.kbase.us) |
| `KBASE_ADMIN_ROLES` | No | Admin roles (default: CDM_JUPYTERHUB_ADMIN) |
| `LOG_LEVEL` | No | Logging level (default: INFO) |

## Local Development

### Without Docker

```bash
# Install dependencies
uv sync --locked

# Configure environment
cp .env.sample .env
# Edit .env with your Slack credentials

# Run locally
uv run uvicorn --host 0.0.0.0 --port 8000 --factory src.main:create_application
```

### With Docker Compose

The included `docker-compose.yaml` provides a complete local development environment with all dependencies (minio-manager-service, MinIO, Redis).

```bash
# Configure environment
cp .env.sample .env
# Edit .env with your Slack credentials (SLACK_BOT_TOKEN, SLACK_SIGNING_SECRET, SLACK_CHANNEL_ID)

# Start all services
docker-compose up --build

# Or run in background
docker-compose up -d --build

# View logs
docker-compose logs -f tenant-access-request-service

# Stop services
docker-compose down
```

**Services started:**
- `tenant-access-request-service` - This service (port 8000)
- `minio-manager-service` - Governance API (port 8003)
- `minio` - Object storage (ports 9002/9003)
- `redis` - Cache (port 6379)

## Testing

```bash
# Run all tests with coverage
PYTHONPATH=. uv run pytest --cov=src tests/ -v

# Run specific test file
PYTHONPATH=. uv run pytest tests/routes/test_requests.py -v

# Run with coverage report
PYTHONPATH=. uv run pytest --cov=src --cov-report=html tests/

# Lint and format
uv run ruff check --fix .
uv run ruff format .
```

## Slack App Setup

See [Slack Integration Setup Guide](docs/slack-setup.md) for detailed instructions on configuring the Slack app.

