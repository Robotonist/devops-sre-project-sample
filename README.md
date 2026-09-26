# DevOps / SRE Project Sample

A production-style monitoring appliance built to demonstrate practical DevOps, SRE, and forward-deployed engineering skills across application delivery, containerization, networking, reliability, CI/CD, and operations.

The application is intentionally small. The operational characteristics are the point of the project.

## What the appliance does

The Ops Appliance monitors HTTP/HTTPS targets and records their health over time.

A target can include:

- an HTTP or HTTPS endpoint
- an expected status code
- a check interval
- a TLS warning threshold
- an optional version endpoint

The appliance schedules checks, queues work through Redis, executes probes in Celery workers, stores results in PostgreSQL, and exposes configuration and history through a FastAPI API.

## What this project demonstrates

- Python 3.12 + FastAPI application delivery
- PostgreSQL durable state and Alembic migrations
- Redis + Celery asynchronous job processing
- recurring scheduling with Celery Beat
- HTTP, latency, TLS, and version probes
- Docker multi-stage builds
- non-root runtime containers
- private container networking
- health and readiness semantics
- structured JSON logging with correlation IDs
- deterministic integration and smoke testing
- GitHub Actions CI
- operator-friendly Makefile commands
- explicit failure boundaries between API, scheduler, worker, broker, and database

See [docs/architecture.md](docs/architecture.md) for a deeper architectural walkthrough.

## Architecture at a glance

```text
                    localhost:8000
                         |
                         v
                  +-------------+
                  | FastAPI API |
                  +------+------+ 
                         |
              +----------+----------+
              |                     |
              v                     v
        +-----------+          +---------+
        | PostgreSQL|          |  Redis  |
        +-----+-----+          +----+----+
              ^                     |
              |                     v
              |              +-------------+
              |              |Celery Worker|
              |              +------+------+ 
              |                     |
              |                     v
              |                monitored
              |                 targets
              |
        +-----+------+
        |Celery Beat |
        +------------+
```

Only the API is published to the host by default. PostgreSQL, Redis, worker, and scheduler stay on the private Compose network.

## Prerequisites

For the normal developer path you need:

- Git
- Docker Desktop or another Docker Engine with Docker Compose
- GNU Make or a compatible `make`

You do **not** need to install Python, pytest, or Ruff on the host for the standard workflow. Tests and linting run in a dedicated development container.

## Operating modes

The project supports two intentionally different runtime paths.

### Development and validation

Docker Compose remains the normal developer workflow. It provides the same API, PostgreSQL, Redis, Worker, and Beat process boundaries in a fast local environment suitable for development, tests, smoke validation, and CI.

```text
Developer workstation
    |
    +-- Docker Compose
         +-- API
         +-- Worker
         +-- Beat
         +-- PostgreSQL
         +-- Redis
```

### Linux appliance

v0.2 adds a production-style single-node appliance deployment:

```text
Mac / operator
     |
     | SSH / HTTP 8000
     v
Ubuntu 26.04 + UFW
     |
     +-- Ansible-managed host configuration
     |
     +-- systemd --user (opsappliance)
          |
          +-- rootless Podman
               +-- ops-api
               +-- ops-worker
               +-- ops-beat
               +-- ops-postgres
               +-- ops-redis
```

The application architecture is intentionally unchanged between the two modes. Docker Compose operates the development stack; systemd supervises the Linux appliance using services generated from Quadlet definitions.

## Linux appliance deployment

The v0.2 appliance requires:

- an Ubuntu 26.04 LTS VM prepared using [docs/runbooks/v0.2-utm-bootstrap.md](docs/runbooks/v0.2-utm-bootstrap.md)
- SSH access from the control machine
- Ansible installed on the control machine
- the `community.general` Ansible collection
- a local inventory copied from `ansible/inventory/local.ini.example`
- a local secrets file copied from `ansible/group_vars/all/secrets.yml.example`
- an explicit published GHCR application image tag

The real inventory and secrets files are intentionally excluded from Git.

Deploy the release image:

```bash
make deploy ANSIBLE_ARGS="-k -K -e ops_appliance_version=v0.2.0"
```

Verify the deployed appliance:

```bash
make verify-appliance ANSIBLE_ARGS="-k -K"
```

The deployment converges the Ubuntu host configuration, deploys the rootless Podman services, applies Alembic database migrations, and waits for the API readiness endpoint before reporting success.

Verify the API directly from the control machine:

```bash
curl --fail http://<guest-ip>:8000/healthz
curl --fail http://<guest-ip>:8000/readyz
```

A ready appliance should return:

```json
{"status":"ready","database":"ok","redis":"ok"}
```

## Quick start

Clone the repository and start the appliance:

```bash
git clone https://github.com/Robotonist/devops-sre-project-sample.git
cd devops-sre-project-sample
make up
```

`make up` creates `.env` from `.env.example` when needed, builds the runtime image, runs migrations, and starts PostgreSQL, Redis, the API, worker, and Beat scheduler.

Check service state:

```bash
make ps
```

Check the API:

```bash
curl http://localhost:8000/healthz
curl http://localhost:8000/readyz
```

Expected readiness response:

```json
{"status":"ready","database":"ok","redis":"ok"}
```

Open the interactive FastAPI documentation at:

```text
http://localhost:8000/docs
```

## Create a monitoring target

This target points back at the API from inside the Compose network, so the demo does not depend on public internet access:

```bash
curl -X POST http://localhost:8000/api/v1/targets \
  -H 'Content-Type: application/json' \
  -d '{
    "name": "self-health",
    "url": "http://api:8000/healthz",
    "interval_seconds": 10,
    "expected_status": 200,
    "tls_warning_days": 30,
    "enabled": true
  }'
```

List targets:

```bash
curl http://localhost:8000/api/v1/targets
```

The scheduler will detect when the target is due, enqueue a task through Redis, and a Celery worker will execute the probe and persist the result in PostgreSQL.

## Run a manual check

Use the target UUID returned by the create call:

```bash
curl -X POST http://localhost:8000/api/v1/targets/<target-id>/check
```

Then retrieve its check history:

```bash
curl http://localhost:8000/api/v1/targets/<target-id>/checks
```

## Inspect logs

```bash
docker compose logs --tail=50 worker
```

Worker logs are structured JSON and include correlation fields such as `target_id`, `task_id`, and `result_id` when relevant.

Example:

```json
{"service":"worker","level":"INFO","message":"target check completed","target_id":"...","task_id":"...","result_id":"..."}
```

## Validation commands

The Makefile is the primary operator/developer interface.

```bash
make build     # build runtime images
make up        # start the local Compose stack
make ps        # show service state
make logs      # follow Compose logs
make migrate   # run Alembic migrations
make test      # run pytest in the dev container
make lint      # run Ruff in the dev container
make check     # run tests + lint in the dev container
make smoke     # run the live vertical-slice smoke test against a running stack
make down      # stop containers but preserve PostgreSQL data
make reset     # stop containers and delete the local PostgreSQL volume
make infra-check                                    # validate Ansible syntax and lint
make deploy ANSIBLE_ARGS="-k -K -e ops_appliance_version=v0.2.0"
make verify-appliance ANSIBLE_ARGS="-k -K"
```

`make reset` is destructive to local database state. Normal shutdown should use `make down`.

## Health semantics

`GET /healthz`

- answers whether the API process is alive
- does not fail simply because another service is temporarily unavailable

`GET /readyz`

- checks whether the API can perform its useful responsibilities
- requires PostgreSQL
- reports Redis independently because read-only API operations can remain useful when queueing is degraded

This distinction is intentional: **alive does not necessarily mean ready**.

## Failure model

The system treats expected target failures as monitoring data rather than application crashes.

Examples include:

- DNS resolution failures
- connection refusal
- timeouts
- unexpected HTTP status codes
- TLS validation failures
- expired certificates
- optional version endpoint failures

A failed target should produce a persisted `CheckResult`; it should not crash the worker.

The processes are also intentionally separated. Stopping the worker does not stop the API, and loss of Redis does not erase durable target configuration or historical results because PostgreSQL is the source of truth.

## CI

Pull requests and pushes to `main` run GitHub Actions validation that:

1. runs tests and lint in the development container
2. builds runtime container images
3. starts the Compose stack
4. verifies database migrations
5. waits for API readiness
6. runs the end-to-end vertical-slice smoke test
7. reports service status
8. always tears the environment down

This provides a clean Linux validation environment independent of the developer workstation.

## Release scope

### v0.1 — local vertical slice

v0.1 established the application and operational boundaries:

```text
target definition
    -> PostgreSQL
    -> scheduler
    -> Redis
    -> Celery worker
    -> probe
    -> CheckResult
    -> API history
```

### v0.2 — Linux appliance

v0.2 extends that same application into a reproducible Linux deployment:

- Ubuntu 26.04 LTS
- Ansible-managed host configuration
- rootless Podman
- systemd user services generated from Quadlet definitions
- UFW firewall policy
- persistent PostgreSQL and ephemeral Redis
- explicit multi-architecture GHCR images
- deployment-time database migrations
- readiness-gated deployment
- reboot recovery and persistence acceptance testing

The application process boundaries remain intentionally unchanged between the Compose and appliance runtimes.

## Roadmap

- **v0.1 — Local vertical slice:** complete
- **v0.2 — Linux appliance:** current
- **v0.3 — Observability:** Prometheus, Grafana, centralized logging, OpenTelemetry
- **v0.4 — Reliability:** alerting, SLOs, failure injection, runbooks, incident exercises
- **v0.5 — Secure delivery:** scanning, SBOMs, signing/attestations, stronger secret handling
- **v0.6 — Lifecycle operations:** backups, restores, upgrades, rollback
- **v1.0 — Interview-ready appliance:** polished demo, threat model, postmortems, reproducible deployment

The project deliberately does not start with Kubernetes. v0.1 established the application boundaries, and v0.2 demonstrates that those same boundaries can be deployed and operated on a Linux host without redesigning the application.

## Documentation

- [Architecture](docs/architecture.md)
- [v0.1 Design](docs/design.md)
- [v0.1 Implementation Plan](docs/superpowers/plans/2026-09-13-v0.1-implementation.md)
- [v0.2 Linux Appliance Design](docs/superpowers/specs/2026-09-14-v0.2-linux-appliance-design.md)
- [v0.2 Linux Appliance Implementation Plan](docs/superpowers/plans/2026-09-14-v0.2-linux-appliance-implementation.md)
- [v0.2 UTM Bootstrap Runbook](docs/runbooks/v0.2-utm-bootstrap.md)
- [v0.2 Acceptance Evidence](docs/validation/v0.2-acceptance.md)
