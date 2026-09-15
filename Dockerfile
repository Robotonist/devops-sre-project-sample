FROM python:3.12.14-slim-bookworm AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN groupadd --system --gid 10001 ops \
    && useradd --system --uid 10001 --gid ops --create-home ops

COPY pyproject.toml alembic.ini ./
COPY app ./app
COPY migrations ./migrations

RUN python -m pip install --no-cache-dir . \
    && chown -R ops:ops /app

USER ops

EXPOSE 8000

FROM base AS dev

USER root
COPY --chown=ops:ops tests ./tests
RUN python -m pip install --no-cache-dir '.[dev]'
USER ops

CMD ["python", "-m", "pytest", "tests", "-v"]

FROM base AS runtime

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
