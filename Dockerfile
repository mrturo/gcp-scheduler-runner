# Multi-stage Docker build for Flask application on Cloud Run
# Optimized for production: Alpine Linux (minimal CVEs), non-root user, minimal dependencies

# Build stage
FROM python:3.11-alpine AS builder

# Install build dependencies
RUN apk add --no-cache \
    gcc \
    musl-dev \
    linux-headers

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --user -r requirements.txt

# Production stage
FROM python:3.11-alpine

# Install runtime dependencies only
RUN apk add --no-cache libstdc++

# Create non-root user for security
RUN addgroup -g 1000 appuser && \
    adduser -D -u 1000 -G appuser appuser

# Set working directory
WORKDIR /app

# Copy Python packages from builder
COPY --from=builder /root/.local /home/appuser/.local

# Copia toda la carpeta src al contenedor
COPY --chown=appuser:appuser src/ ./src/

# Switch to non-root user
USER appuser

# Add local packages to PATH
ENV PATH=/home/appuser/.local/bin:$PATH

# Cloud Run will set PORT environment variable

# Expose port (Cloud Run expects 8080 by default)
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:${PORT}/health').read()" || exit 1

# Inicia la aplicación Flask desde el paquete src
CMD ["python", "-m", "src.app"]
