# =========================================================================
# SLA, SLO, SLI Monitoring Engine - Dockerfile
# =========================================================================

FROM python:3.11-slim

LABEL maintainer="SRE Reliability Team"
LABEL description="Production SLA, SLO, SLI Monitoring and Chaos Observability Engine"

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=5000 \
    DATABASE_PATH=/app/data/sla_monitor.db \
    SIMULATOR_ENABLED=true

# Create app directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency definition and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY engine/ /app/engine/
COPY static/ /app/static/
COPY templates/ /app/templates/
COPY run.py /app/run.py

# Create persistent storage folder for SQLite
RUN mkdir -p /app/data && chmod 777 /app/data

# Expose port
EXPOSE 5000

# Healthcheck
HEALTHCHECK --interval=15s --timeout=5s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:5000/api/health || exit 1

# Start application
CMD ["python", "run.py", "--host", "0.0.0.0", "--port", "5000"]
