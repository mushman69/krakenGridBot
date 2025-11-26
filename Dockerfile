# Enhanced GridBot with PnL Tracking - Docker Setup
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV DOCKER_DEPLOYMENT=1
ENV TZ=UTC

# Install system dependencies for matplotlib
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libfreetype6-dev \
    libpng-dev \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt ./

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy bot files
COPY improved_gridbot.py pnl_analyzer.py db_viewer.py ./
COPY kraken.env ./

# Copy and set up entrypoint script
COPY docker-entrypoint.sh /app/docker-entrypoint.sh
RUN chmod +x /app/docker-entrypoint.sh

# Create directories for data persistence with proper permissions
RUN mkdir -p /app/data /app/exports /app/charts /app/logs && \
    chmod -R 777 /app/data /app/exports /app/charts /app/logs

# Set the database path to the persistent volume
ENV DATABASE_FILE=/app/data/gridbot_pnl.db

# Expose volume for data persistence
VOLUME ["/app/data", "/app/exports", "/app/charts"]

# Use entrypoint to fix permissions on startup
ENTRYPOINT ["/app/docker-entrypoint.sh"]

# Default command
CMD ["python", "improved_gridbot.py"]
