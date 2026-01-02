# Multi-stage Dockerfile for PrenoPinzo Django Application
# Stage 1: Build dependencies
FROM python:3.12-slim as builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Create and activate virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt gunicorn

# Stage 2: Production image
FROM python:3.12-slim as production

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH" \
    DJANGO_SETTINGS_MODULE=PrenoPinzo.settings_prod

WORKDIR /app

# Install runtime dependencies (cron, gosu, procps for debugging)
RUN apt-get update && apt-get install -y --no-install-recommends \
    cron \
    gosu \
    procps \
    && rm -rf /var/lib/apt/lists/*

# Copy crontab and convert Windows line endings to Unix
COPY crontab /etc/cron.d/prenopinzo-cron
RUN sed -i 's/\r$//' /etc/cron.d/prenopinzo-cron && \
    chmod 0644 /etc/cron.d/prenopinzo-cron && \
    touch /var/log/cron.log

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv

# Copy application code
COPY . .

# Create non-root user for security
RUN useradd --create-home --shell /bin/bash appuser && \
    chown -R appuser:appuser /app

# Create directories for static files and data
RUN mkdir -p /app/staticfiles /app/data && \
    chown -R appuser:appuser /app/staticfiles /app/data /var/log/cron.log

# Make entrypoint executable
RUN chmod +x /app/entrypoint.sh && \
    sed -i 's/\r$//' /app/entrypoint.sh

# USER appuser removed to allow entrypoint to run as root (start cron) and drop privileges


# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health/')" || exit 1

ENTRYPOINT ["/app/entrypoint.sh"]
CMD ["daphne", "-b", "0.0.0.0", "-p", "8000", "PrenoPinzo.asgi:application"]
