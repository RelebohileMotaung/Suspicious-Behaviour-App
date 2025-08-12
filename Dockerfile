# MongoDB-optimized Dockerfile for Render
FROM python:3.9-slim as builder

WORKDIR /app
COPY requirements.txt .

# Install essential build dependencies and MongoDB client tools
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    gcc \
    python3-dev \
    mongodb-clients \
    && \
    pip install --user -r requirements.txt

FROM python:3.9-slim

WORKDIR /app

# Install MongoDB client tools and system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    libgl1 \
    ffmpeg \
    mongodb-clients \
    && \
    rm -rf /var/lib/apt/lists/*

# Copy Python packages from builder
COPY --from=builder /root/.local /root/.local
COPY . .

# Ensure scripts in .local are usable
ENV PATH=/root/.local/bin:$PATH
ENV PYTHONPATH=/app

# MongoDB connection environment variables
ENV MONGODB_URI=mongodb://localhost:27017/
ENV MONGODB_DATABASE=cash_monitor
ENV MONGODB_TIMEOUT=5000

# Render-specific ports
EXPOSE 10000
ENV PORT=10000
ENV STREAMLIT_SERVER_PORT=10000

# Create directories and set permissions
RUN mkdir -p telemetry full_frames && \
    chmod -R a+w telemetry full_frames

# Initialize MongoDB connection and setup
RUN python -c "from app.db.mongo_config import init_mongodb; init_mongodb()"

# Health check for MongoDB connectivity
HEALTHCHECK --interval=30s --timeout=30s --start-period=60s --retries=3 \
    CMD python -c "from app.db.mongo_config import check_mongodb_connection; check_mongodb_connection()"

# Render-compatible entrypoint
CMD ["streamlit", "run", "app.py", "--server.port=10000", "--server.address=0.0.0.0"]
