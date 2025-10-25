# Multi-stage build for RugDetector
# Stage 1: Base image with Node.js and Python
FROM node:18-bullseye-slim

# Install Python and system dependencies
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    python3-dev \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy package files
COPY package*.json ./

# Install Node.js dependencies
RUN npm ci --only=production

# Copy Python requirements
COPY requirements.txt ./

# Install Python dependencies
RUN pip3 install --no-cache-dir -r requirements.txt

# Build and export ONNX model without ZipMap (compatible with onnxruntime-node)
RUN python3 training/train_model.py

# Cache-busting ARG to force rebuild of application code layer
ARG CACHE_BUST=1

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p logs

# Set permissions for zkML binary (if it exists)
RUN chmod +x zkml-jolt-atlas/target/release/zkml-jolt-core 2>/dev/null || true

# Expose port
EXPOSE 3000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:3000/health || exit 1

# Clear Python bytecode cache and start
CMD ["sh", "-c", "find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true && find . -type f -name '*.pyc' -delete 2>/dev/null || true && PYTHONDONTWRITEBYTECODE=1 node api/server.js"]
