# syntax=docker/dockerfile:1
# MCP packaging image. Tools live in-process on FastAPI (/mcp/tools, /mcp/call).
# Build from repo root: docker build -f mcp/Dockerfile -t enterpriseflow-mcp .
FROM python:3.12-slim AS builder
WORKDIR /src
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential \
    && rm -rf /var/lib/apt/lists/*
COPY pyproject.toml README.md ./
COPY app ./app
RUN pip install --upgrade pip && pip install --prefix=/install .

FROM python:3.12-slim AS runtime
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 HOME=/home/app PATH=/usr/local/bin:$PATH \
    EF_COMPONENT=mcp
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --gid 10001 app \
    && useradd --uid 10001 --gid app --create-home --home-dir /home/app app
COPY --from=builder /install /usr/local
COPY alembic ./alembic
COPY alembic.ini ./
COPY data ./data
COPY evaluations ./evaluations
COPY scripts/entrypoint.sh ./scripts/entrypoint.sh
RUN chmod +x ./scripts/entrypoint.sh \
    && mkdir -p /app/mlruns \
    && chown -R app:app /app /home/app
USER app
LABEL com.enterpriseflow.component=mcp
EXPOSE 8000
HEALTHCHECK --interval=15s --timeout=5s --start-period=40s --retries=5 \
  CMD curl -fsS http://127.0.0.1:8000/mcp/tools || exit 1
# # ponytail: same process as API; separate image for compose/scale naming only
CMD ["./scripts/entrypoint.sh"]
