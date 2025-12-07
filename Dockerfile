# Enhanced GridBot with PnL Tracking - Docker Setup
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV DOCKER_DEPLOYMENT=1
ENV TZ=UTC

# Install system dependencies for matplotlib
# Workaround for GPG signature issues and optimize for disk space
# Use minimal space by cleaning during each step
RUN apt-get clean && \
    rm -rf /var/lib/apt/lists/* /var/cache/apt/archives/* && \
    echo "Acquire::Check-Valid-Until false;" > /etc/apt/apt.conf.d/99no-check-valid-until && \
    echo "APT::Get::AllowUnauthenticated true;" >> /etc/apt/apt.conf.d/99no-check-valid-until && \
    echo "APT::Get::Assume-Yes true;" >> /etc/apt/apt.conf.d/99no-check-valid-until && \
    echo "APT::Install-Recommends false;" >> /etc/apt/apt.conf.d/99no-check-valid-until && \
    apt-get update -o Acquire::Check-Valid-Until=false -o Acquire::AllowInsecureRepositories=true 2>&1 | grep -v "^W:" || true && \
    apt-get install -y --no-install-recommends --allow-unauthenticated \
    ca-certificates \
    gcc \
    g++ \
    libfreetype6-dev \
    libpng-dev \
    pkg-config \
    && apt-get clean && \
    rm -rf /var/lib/apt/lists/* /var/cache/apt/archives/* /etc/apt/apt.conf.d/99no-check-valid-until

# Copy requirements first for better caching
COPY requirements.txt ./

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt && \
    # Remove build tools after Python packages are installed (they're only needed for compilation)
    apt-get purge -y gcc g++ && \
    apt-get autoremove -y && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* /var/cache/apt/archives/*

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
