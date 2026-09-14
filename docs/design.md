# Ops Appliance v0.1 Design

Date: 2026-09-13
Status: Proposed / approved in chat for initial implementation

## 1. Purpose

`ops-appliance` is a portfolio project that demonstrates the ability to deploy, secure, operate, monitor, troubleshoot, and evolve a small production-style software appliance.

The project is optimized for DevOps Engineer, Site Reliability Engineer, Platform Engineer, and Forward Deployed Engineer interviews. The application is intentionally modest; the deployment and operational characteristics are the primary product.

Version 0.1 is a local-development release that runs on Docker Desktop on macOS. Later releases will move the same service boundaries to an Ubuntu appliance using Podman, systemd/Quadlet, Ansible, and infrastructure-as-code.

## 2. v0.1 Success Criteria

A new developer can clone the repository, create local configuration, start the system with Docker Compose, and interact with the API through FastAPI's built-in OpenAPI UI.

The system must support one complete monitoring flow:

1. Create a monitoring target through the API.
2. Persist the target in PostgreSQL.
3. Schedule recurring checks through Celery Beat.
4. Queue probe work through Redis.
5. Execute probes in a dedicated Celery worker.
6. Perform HTTP, latency, TLS, and optional application-version checks.
7. Persist probe results in PostgreSQL.
8. Retrieve targets and historical results through the API.

Version 0.1 also includes tests, container health checks, structured logging, database migrations, a Makefile, and GitHub Actions CI.

## 3. Explicit Non-Goals for v0.1

The following are intentionally deferred:

- React or other custom browser dashboard
- authentication and user management
- alert delivery
- Grafana, Prometheus, Loki, and OpenTelemetry
- production TLS termination
- Podman / Quadlet
- Ansible
- OpenTofu
- production secrets management
- backup / restore
- upgrade / rollback automation
- Kubernetes

Deferring these items keeps v0.1 focused on one working vertical slice while preserving clear extension points for later releases.

## 4. Technology Choices

### Application

- Python 3.12+
- FastAPI for the HTTP API
- SQLAlchemy for persistence
- Alembic for schema migrations
- Pydantic for request/response validation
- Celery for background jobs
- Redis as Celery broker
- PostgreSQL as durable application state
- `httpx` for HTTP probes
- Python `ssl` / socket facilities for TLS certificate inspection where needed

### Development and Delivery

- Docker Desktop on macOS
- Docker Compose for local orchestration
- Pytest for tests
- Ruff for linting/format checks
- GitHub Actions for CI
- Makefile as the primary developer command interface

## 5. Service Architecture

v0.1 contains five logical runtime services:

### API

Responsibilities:

- validate requests
- create and read monitoring targets
- expose check history
- expose liveness and readiness endpoints
- enqueue immediate checks when requested

The API does not perform probes directly.

### PostgreSQL

Responsibilities:

- source of truth for monitoring target configuration
- durable storage for probe results

Redis must never be the only location containing target configuration or historical checks.

### Redis

Responsibilities:

- Celery message broker
- transient coordination between schedulers and workers

Redis data is disposable. Loss of Redis must not destroy durable application state.

### Celery Worker

Responsibilities:

- receive probe jobs
- load target configuration
- execute monitoring probes
- write results to PostgreSQL
- classify expected probe failures without crashing the worker

### Celery Beat

Responsibilities:

- trigger recurring probe jobs

Beat remains a separate process from the worker so scheduling and execution have explicit operational boundaries.

## 6. Local Networking

All services communicate through a private Docker Compose network.

For v0.1:

- API publishes `localhost:8000` to the developer machine.
- PostgreSQL is not published to the host by default.
- Redis is not published to the host by default.
- Worker and Beat publish no ports.

A later optional development override may publish PostgreSQL for debugging, but this is not part of the default path.

The design establishes the future security principle that data-plane services should not be externally reachable merely because they are containerized.

## 7. Data Model

### Target

Fields:

- `id`: UUID
- `name`: human-readable unique name
- `url`: primary HTTP/HTTPS endpoint
- `interval_seconds`: positive integer; v0.1 enforces a reasonable minimum
- `expected_status`: expected HTTP status, default `200`
- `tls_warning_days`: warning threshold, default `30`
- `version_url`: optional endpoint used to retrieve an application version
- `enabled`: boolean
- `created_at`: UTC timestamp
- `updated_at`: UTC timestamp

### CheckResult

Fields:

- `id`: UUID
- `target_id`: foreign key to Target
- `started_at`: UTC timestamp
- `completed_at`: UTC timestamp
- `status`: normalized state such as `healthy`, `degraded`, or `failed`
- `http_status`: nullable integer
- `latency_ms`: nullable numeric value
- `tls_valid`: nullable boolean
- `tls_expires_at`: nullable UTC timestamp
- `tls_days_remaining`: nullable integer
- `version`: nullable string
- `error_type`: nullable stable machine-readable value
- `error_message`: nullable sanitized diagnostic text

Check results are immutable historical records after creation.

## 8. Probe Behavior

A probe executes the following stages independently where applicable:

1. Parse and validate the target URL.
2. Perform an HTTP request with a bounded timeout.
3. Record status code and elapsed latency.
4. For HTTPS targets, inspect certificate validity and expiration.
5. When `version_url` is configured, request the endpoint and capture a short normalized version value.
6. Determine the overall normalized status.
7. Persist the result even when part of the probe fails.

Expected network failures are data, not application crashes. Examples include DNS errors, timeouts, connection refusal, TLS validation failure, and unexpected HTTP status codes.

v0.1 will not follow arbitrary unbounded redirects or download large response bodies.

## 9. API Boundaries

All application endpoints are versioned under `/api/v1`.

Minimum API:

- `POST /api/v1/targets`
- `GET /api/v1/targets`
- `GET /api/v1/targets/{target_id}`
- `GET /api/v1/targets/{target_id}/checks`
- `POST /api/v1/targets/{target_id}/check`
- `GET /healthz`
- `GET /readyz`

FastAPI's `/docs` endpoint is the v0.1 interactive operator interface.

### Liveness

`/healthz` answers whether the API process is alive. It must not become unhealthy merely because a dependency is temporarily unavailable.

### Readiness

`/readyz` checks whether the API is ready to serve its normal responsibilities. PostgreSQL availability is required. Redis availability may be reported as a degraded dependency because read-only API operations can still function when queueing is unavailable.

## 10. Error Handling

The API returns structured errors and appropriate HTTP status codes.

Examples:

- validation failure -> `422`
- target not found -> `404`
- duplicate unique target name -> `409`
- database unavailable -> `503`
- queue unavailable when requesting a check -> `503`

Internal exception traces are logged but not returned in API responses.

Probe errors are recorded on `CheckResult` and do not propagate as worker crashes for ordinary network failures.

## 11. Logging

Each application process writes structured logs to stdout/stderr so Docker can capture them without application-managed log files.

Useful fields include:

- timestamp
- level
- service
- message
- target_id when relevant
- check_id when relevant
- task_id for Celery operations

Secrets and complete response bodies are never logged.

This logging format is chosen so later releases can forward the same streams into Loki or another log platform without redesigning the application.

## 12. Container Design

Each custom image will:

- use a small pinned Python base image
- install dependencies reproducibly
- run application code as a non-root user where practical
- avoid embedding secrets
- use explicit health checks where meaningful
- terminate correctly on SIGTERM

Compose uses named volumes for PostgreSQL data and explicit service dependencies plus health checks where dependency ordering matters.

The API, worker, and Beat may initially share one application image with different commands. This reduces duplicate build logic while keeping runtime processes separate.

## 13. Developer Interface

The Makefile is the main interface rather than requiring developers to remember long Compose commands.

Initial commands:

- `make build`
- `make up`
- `make down`
- `make logs`
- `make migrate`
- `make test`
- `make lint`
- `make check`

`make check` runs the local validation suite expected before a commit.

## 14. Configuration

A committed `.env.example` documents required local values.

Real `.env` files are ignored by Git.

v0.1 may use environment variables for local development credentials because it is explicitly a development release. Production-grade secret handling is a later milestone and will replace this mechanism for the appliance deployment.

No real credentials will be committed.

## 15. Testing Strategy

### Unit tests

Cover pure probe and status-classification behavior without requiring containers or external services.

Examples:

- expected status classification
- TLS expiration calculations
- timeout/error normalization
- version-response normalization

### API tests

Verify request validation, target CRUD/read paths used in v0.1, health endpoints, and error mapping.

### Integration tests

Run against PostgreSQL and Redis and verify the vertical slice:

1. create target
2. enqueue check
3. worker executes check
4. result persists
5. API returns result

Tests should prefer deterministic local fixtures rather than relying on public internet endpoints.

### Container smoke test

CI starts the Compose stack, waits for readiness, performs a minimal API interaction, and fails if the stack does not become healthy.

## 16. CI Design

GitHub Actions v0.1 performs:

1. dependency installation
2. linting
3. unit/API tests
4. container image build
5. integration/smoke test using service containers or Compose

Security scanning, SBOM generation, signing, and attestations are planned for subsequent releases once the base build is stable.

## 17. Repository Shape

Initial structure:

```text
ops-appliance/
├── README.md
├── Makefile
├── .env.example
├── .gitignore
├── compose.yaml
├── pyproject.toml
├── alembic.ini
├── app/
│   ├── api/
│   ├── core/
│   ├── db/
│   ├── models/
│   ├── probes/
│   ├── schemas/
│   └── worker/
├── migrations/
├── tests/
│   ├── unit/
│   ├── api/
│   └── integration/
├── docs/
│   ├── architecture.md
│   └── superpowers/specs/
└── .github/workflows/
```

The structure may evolve as implementation reveals better boundaries, but responsibilities should remain separated rather than accumulating in one large module.

## 18. Planned Release Progression

### v0.1 — Local vertical slice

FastAPI, PostgreSQL, Redis, Celery worker/Beat, probes, Compose, migrations, tests, CI.

### v0.2 — Linux appliance

Ubuntu, Podman, systemd/Quadlet, Ansible, network/firewall hardening, deployment validation.

### v0.3 — Observability

Prometheus metrics, Grafana, centralized logs, OpenTelemetry, service-level dashboards.

### v0.4 — Alerting and reliability

Alertmanager/webhooks, SLOs, failure injection, runbooks, incident exercises.

### v0.5 — Secure delivery

Image scanning, SBOMs, signatures/attestations, stronger secrets management.

### v0.6 — Lifecycle operations

Backups, restore testing, upgrades, versioned manifests, rollback.

### v1.0 — Interview-ready appliance

Polished read-only dashboard, architecture diagrams, recorded demo, documented threat model, postmortems, and reproducible deployment.

## 19. Architectural Rationale

The project intentionally begins with a small application and multiple operationally meaningful components. FastAPI, PostgreSQL, Redis, Celery Worker, and Celery Beat provide enough distributed-system behavior to demonstrate networking, dependency management, health semantics, job queues, persistence, observability, and failure handling without turning the exercise into a frontend product project.

Docker Compose is a development implementation detail, not the final deployment architecture. Keeping application services independently runnable allows later migration to Podman/Quadlet and eventually, if useful, Kubernetes without redesigning the application.
