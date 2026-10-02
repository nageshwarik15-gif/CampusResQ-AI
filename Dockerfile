# CampusResQ AI: Multi-Agent AI Campus Emergency Coordinator
# Container Architecture conforming to SDD §10.1

FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source code
COPY . .

# Expose FastAPI & WebSocket port
EXPOSE 8000

# Health check probe (SDD §10.2)
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/healthz || exit 1

# Launch Server
CMD ["python", "run_server.py"]
