FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

COPY pyproject.toml README.md ./
COPY app ./app
COPY alembic ./alembic
COPY alembic.ini ./
COPY data ./data
COPY scripts/entrypoint.sh ./scripts/entrypoint.sh

RUN pip install --upgrade pip && pip install . \
    && chmod +x ./scripts/entrypoint.sh

EXPOSE 8000

CMD ["./scripts/entrypoint.sh"]
