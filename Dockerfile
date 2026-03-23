# Claude Swarm — Multi-Instance Orchestration
# Multi-stage Dockerfile for production deployment

FROM python:3.11-slim as builder

WORKDIR /build

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --no-cache-dir -r requirements.txt

COPY setup.py README.md ./
COPY src/ ./src/
RUN pip install --no-cache-dir .

FROM python:3.11-slim as production

LABEL org.opencontainers.image.title="Claude Swarm"
LABEL org.opencontainers.image.description="Multi-Instance AI Orchestration"
LABEL org.opencontainers.image.vendor="1450 Enterprises LLC"

RUN groupadd --gid 1000 swarm && \
    useradd --uid 1000 --gid 1000 --create-home --shell /bin/bash swarm

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

WORKDIR /app
COPY --chown=swarm:swarm src/ ./src/
COPY --chown=swarm:swarm config/ ./config/
COPY --chown=swarm:swarm workflows/ ./workflows/

RUN mkdir -p /app/logs /app/data && chown -R swarm:swarm /app

USER swarm

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app/src

EXPOSE 8766

HEALTHCHECK --interval=15s --timeout=3s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8766/health || exit 1

CMD ["python", "-m", "uvicorn", "swarm.api.server:create_app", "--factory", "--host", "0.0.0.0", "--port", "8766"]
