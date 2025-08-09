# Render-specific optimizations
FROM python:3.9-slim as builder

WORKDIR /app
COPY requirements.txt .

# Install only essential build deps
RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc python3-dev && \
    pip install --user -r requirements.txt

FROM python:3.9-slim

WORKDIR /app

# Copy only what's needed from builder
COPY --from=builder /root/.local /root/.local
COPY . .

# Render-specific requirements
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    libgl1 \
    ffmpeg && \
    rm -rf /var/lib/apt/lists/*

# Ensure scripts in .local are usable
ENV PATH=/root/.local/bin:$PATH
ENV PYTHONPATH=/app

# Render needs these explicit ports
EXPOSE 10000
ENV PORT=10000
ENV STREAMLIT_SERVER_PORT=10000

# Initialize DB and permissions
RUN mkdir -p telemetry full_frames && \
    chmod -R a+w telemetry full_frames && \
    python -c "from app import init_db; init_db()"

# Healthcheck for Render
HEALTHCHECK --interval=30s --timeout=30s CMD curl -f http://localhost:$PORT/_stcore/health

# Render-compatible entrypoint
CMD streamlit run app.py --server.port=$PORT --server.address=0.0.0.0
