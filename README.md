AsystQA is a multi-agent software QA workflow platform for automated code review, test generation, security analysis, and transparent reporting. It combines a FastAPI backend analysis pipeline with a React/Vite command center for running scans, reviewing findings, and exporting QA reports.

## What It Does

- Runs source code through planner, reviewer, security, tester, and reporter agents.
- Produces structured QA reports with score, risk level, issues, suggested tests, timings, and trace metadata.
- Supports synchronous scans and queued asynchronous scan workflows.
- Includes secret redaction, encrypted local history, tamper-evident audit logs, correlation IDs, rate limiting, and security headers.
- Exposes Prometheus metrics and health/readiness endpoints for operations.
- Provides a frontend dashboard for scan execution, report review, history, settings, pricing, and marketing pages.

## Repository Layout

```text
AsystQA/
|-- backend/              FastAPI API, agents, auth, services, schemas, scripts
|-- frontend/             React + Vite command center
|-- docs/                 Testing notes and implementation reports
|-- monitoring/           Prometheus configuration
|-- tests/                Root backend foundation tests
|-- docker-compose.yml    API, Prometheus, Grafana, and Redis services
|-- Dockerfile            Backend API container
|-- Makefile              Common development commands
`-- SECURITY.md           Security policy
```

## Tech Stack

- Backend: Python 3.11+, FastAPI, Uvicorn, Pydantic, pytest
- Frontend: React 19, Vite, React Router, ESLint
- Security: JWT, MFA/TOTP support, RBAC, AES-GCM encrypted storage, HMAC integrity checks, audit logging
- Observability: Prometheus metrics, OpenTelemetry hooks, structured logs
- Local infrastructure: Docker Compose, Prometheus, Grafana, Redis

## Prerequisites

- Python 3.11 or newer
- Node.js and npm
- Docker Desktop, optional for containerized local services
- Make, optional convenience wrapper

## Quick Start

### 1. Clone and install backend dependencies

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r backend\requirements.txt
```

### 2. Configure backend environment

```powershell
Copy-Item backend\.env.example backend\.env
python backend\scripts\generate_keys.py --output-dir backend\keys
```

Then update `backend\.env` with generated keys where needed. For local development, `AUTH_REQUIRED=false` allows unauthenticated analysis requests. For protected API testing, set `AUTH_REQUIRED=true`.

### 3. Run the backend

```powershell
uvicorn main:app --reload --app-dir backend
```

The API runs at `http://localhost:8000`.

### 4. Install and run the frontend

```powershell
cd frontend
npm install
npm run dev
```

The frontend usually runs at `http://localhost:5173`.

If the API runs somewhere else, create `frontend\.env.local`:

```text
VITE_API_BASE_URL=http://localhost:8000
```

## Common Commands

From the repository root:

```powershell
make dev       # run the backend with Uvicorn
make test      # run pytest
make lint      # run ruff and mypy
make build     # build the frontend
make docker-up # start Docker Compose services
```

Without Make:

```powershell
python -m pytest
ruff check backend tests
mypy backend
cd frontend; npm run lint; npm run build
```

## Docker

Start the API and local observability stack:

```powershell
docker compose up --build
```

Services:

- API: `http://localhost:8000`
- Prometheus: `http://localhost:9090`
- Grafana: `http://localhost:3000`
- Redis: `localhost:6379`

The API container reads `backend/.env.example` by default in `docker-compose.yml`. For realistic local or production-like runs, point Compose at a real environment file with generated secrets.

## API Overview

Health and status:

- `GET /healthz`
- `GET /readyz`
- `GET /livez`
- `GET /startupz`
- `GET /metrics`
- `GET /security/status`

Analysis:

- `POST /analyze`
- `POST /v1/analyze`
- `POST /api/v1/analyze`
- `GET /v1/agents`
- `GET /v1/history`
- `POST /v1/scans`
- `GET /v1/results/{scan_id}`

Authentication:

- `POST /api/v1/auth/register`
- `POST /api/v1/auth/login`
- `POST /api/v1/auth/logout`
- `POST /api/v1/auth/refresh`
- `GET /api/v1/auth/mfa/setup`
- `POST /api/v1/auth/mfa/verify`
- `GET /api/v1/auth/me`

Example scan:

```powershell
Invoke-RestMethod http://localhost:8000/analyze `
  -Method Post `
  -ContentType "application/json" `
  -Body '{"code":"const api_key = \"abc123\"; console.log(api_key);","language":"javascript"}'
```

## Testing

Run the root backend foundation suite:

```powershell
python -m pytest
```

Run frontend checks:

```powershell
cd frontend
npm run lint
npm run build
```

Run backend security validation helpers:

```powershell
python backend\scripts\validate_security.py
python backend\scripts\quick_test.py
```

## Security Notes

AsystQA includes a Zero Trust-oriented backend foundation:

- Optional bearer authentication with JWTs.
- MFA enrollment and verification endpoints.
- Role-based access control for protected resources.
- Secret and PII redaction before persistence.
- Encrypted history storage with integrity signatures.
- Append-only audit logs with hash-chain integrity.
- Rate limiting, security headers, CORS controls, and structured error responses.

Before production use:

- Generate fresh RSA, encryption, audit, and memory integrity keys.
- Set `ENVIRONMENT=production` and `DEBUG=false`.
- Set exact `ALLOWED_ORIGINS`.
- Set `AUTH_REQUIRED=true` and consider `MFA_REQUIRED=true`.
- Store secrets in a vault or managed secret store.
- Review [SECURITY.md](SECURITY.md) and [backend/README_SECURITY.md](backend/README_SECURITY.md).

## Documentation

- [Security policy](SECURITY.md)
- [Backend security guide](backend/README_SECURITY.md)
- [Implementation summary](backend/IMPLEMENTATION_SUMMARY.md)
- [Implementation completion report](backend/IMPLEMENTATION_COMPLETE.md)
- [Testing report](docs/TESTING_REPORT.md)
- [Frontend README](frontend/README.md)

## License

This project is licensed under the terms in [LICENSE](LICENSE).