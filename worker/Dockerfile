# syntax=docker/dockerfile:1
# Optional batch worker (evaluations / offline jobs). Not required for online demo.
# Build: docker build -f worker/Dockerfile -t enterpriseflow-worker .
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
    EF_COMPONENT=worker
RUN groupadd --gid 10001 app \
    && useradd --uid 10001 --gid app --create-home --home-dir /home/app app
COPY --from=builder /install /usr/local
COPY evaluations ./evaluations
COPY data ./data
RUN mkdir -p /app/mlruns && chown -R app:app /app /home/app
USER app
LABEL com.enterpriseflow.component=worker
# one-shot eval; compose can schedule or run --rm
CMD ["python", "-c", "from app.eval_runner import run_all_and_log; import json; print(json.dumps(run_all_and_log(), default=str))"]
