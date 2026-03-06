# GridOS — Open Energy Operating System
# Multi-stage Docker build for production deployment

# ── Stage 1: Builder ─────────────────────────────────────────────
FROM python:3.11-slim AS builder

WORKDIR /build

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for layer caching
COPY requirements/ requirements/
RUN pip install --no-cache-dir --prefix=/install \
    -r requirements/base.txt \
    -r requirements/prod.txt

# Copy source and install package
COPY src/ src/
COPY pyproject.toml .
COPY README.md .
COPY LICENSE .
RUN pip install --no-cache-dir --prefix=/install .

# ── Stage 2: Runtime ─────────────────────────────────────────────
FROM python:3.11-slim AS runtime

# OCI standard labels for GitHub Container Registry discoverability
LABEL org.opencontainers.image.title="GridOS"
LABEL org.opencontainers.image.description="Open Energy Operating System — vendor-neutral middleware for Distributed Energy Resources (DERs)"
LABEL org.opencontainers.image.url="https://github.com/iceccarelli/GridOS"
LABEL org.opencontainers.image.source="https://github.com/iceccarelli/GridOS"
LABEL org.opencontainers.image.documentation="https://github.com/iceccarelli/GridOS/tree/main/docs"
LABEL org.opencontainers.image.licenses="MIT"
LABEL org.opencontainers.image.vendor="GridOS Contributors"
LABEL org.opencontainers.image.version="0.1.0"

# Install runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN groupadd -r gridos && useradd -r -g gridos -d /app -s /sbin/nologin gridos

# Copy installed packages from builder
COPY --from=builder /install /usr/local

# Copy application
WORKDIR /app
COPY src/ src/
COPY data/ data/

# Create directories for models and logs
RUN mkdir -p /app/models_cache /app/logs && \
    chown -R gridos:gridos /app

USER gridos

# Environment
ENV PYTHONPATH=/app/src \
    PYTHONUNBUFFERED=1 \
    GRIDOS_ENV=production \
    GRIDOS_LOG_LEVEL=INFO

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

EXPOSE 8000

# Run with uvicorn
CMD ["uvicorn", "gridos.main:app", \
     "--host", "0.0.0.0", \
     "--port", "8000", \
     "--workers", "4", \
     "--access-log", \
     "--log-level", "info"]
