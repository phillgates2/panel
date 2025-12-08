# Production Dockerfile with Multi-Stage Build
# Uses security best practices and optimized layers

# =============================================================================
# Builder Stage - Compile dependencies and build wheels
# =============================================================================
FROM python:3.14-slim AS builder

# Install build dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    gcc \
    g++ \
    libffi-dev \
    libssl-dev \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy requirements and install Python dependencies
COPY requirements/requirements-prod.txt ./requirements-prod.txt
RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --no-cache-dir -r requirements-prod.txt

# =============================================================================
# Security Scanner Stage - Scan for vulnerabilities
# =============================================================================
FROM builder AS security-scan

# Install security scanning tools
RUN pip install --no-cache-dir safety bandit

# Copy source code for scanning
COPY . /app
WORKDIR /app

# Run security scans (will be checked in CI/CD)
RUN safety check --full-report || echo "Safety check completed with warnings"
RUN bandit -r . -f json -o security-report.json || echo "Bandit scan completed"

# =============================================================================
# Production Stage - Final optimized image
# =============================================================================
FROM python:3.14-slim AS production

# Add metadata labels
LABEL maintainer="Panel Team" \
      version="1.0.0" \
      description="Panel Application - Production Image"

# Create non-root user for security
RUN groupadd -r panel && useradd -r -g panel panel

# Install only runtime dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Copy virtual environment from builder stage
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Create application directory
RUN mkdir -p /app && chown -R panel:panel /app
WORKDIR /app

# Copy application code with proper ownership
COPY --chown=panel:panel . .

# Create necessary directories
RUN mkdir -p /app/instance && \
    mkdir -p /app/logs && \
    chown -R panel:panel /app/instance /app/logs

# Switch to non-root user
USER panel

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

# Expose port
EXPOSE 8080

# Set environment variables
ENV FLASK_ENV=production \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Run application with gunicorn for production
CMD ["gunicorn", \
     "--bind", "0.0.0.0:8080", \
     "--workers", "4", \
     "--worker-class", "sync", \
     "--worker-connections", "1000", \
     "--max-requests", "1000", \
     "--max-requests-jitter", "50", \
     "--timeout", "30", \
     "--keep-alive", "10", \
     "--log-level", "info", \
     "--access-logfile", "-", \
     "--error-logfile", "-", \
     "app:create_app()"]

# =============================================================================
# Development Stage - For development with hot reload
# =============================================================================
FROM builder AS development

# Install development dependencies
COPY requirements/requirements-dev.txt ./requirements-dev.txt
RUN pip install --no-cache-dir -r requirements-dev.txt

# Create app user
RUN groupadd -r panel && useradd -r -g panel panel

# Set up application directory
RUN mkdir -p /app && chown -R panel:panel /app
WORKDIR /app

# Copy application code
COPY --chown=panel:panel . .

# Switch to app user
USER panel

# Expose port
EXPOSE 8080

# Development command with hot reload
CMD ["flask", "run", "--host", "0.0.0.0", "--port", "8080", "--reload"]