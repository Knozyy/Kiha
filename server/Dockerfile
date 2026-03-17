# ============================
# Stage 1: Builder
# ============================
FROM python:3.12-slim AS builder

WORKDIR /app

COPY server/pyproject.toml .

RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir .

# ============================
# Stage 2: Runtime
# ============================
FROM python:3.12-slim AS runtime

LABEL maintainer="Kiha Team"
LABEL description="Kiha AI Smart Glasses — FastAPI Server"

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application source
COPY server/src/ ./src/

# Set Python path for module resolution
ENV PYTHONPATH=/app/src
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

EXPOSE 8000 8001 9000/udp

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
