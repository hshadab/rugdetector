# Multi-stage build for RugDetector
# Stage 1: Base image with Node.js and Python
FROM node:18-bullseye-slim

# Install Python, Rust, and system dependencies
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    python3-dev \
    build-essential \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Install Rust for building zkML binary with MAX_TENSOR_SIZE=1024
RUN curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
ENV PATH="/root/.cargo/bin:${PATH}"

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

# Cache-busting ARG to force rebuild of application code layer
ARG CACHE_BUST=1

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p logs

# Build zkML binary from personal fork with MAX_TENSOR_SIZE=1024 modifications
# This ALWAYS builds - no fallbacks or optional behavior
RUN echo "Building zkML binary from hshadab/jolt-atlas fork..." && \
    cd zkml-jolt-atlas && \
    git submodule update --init --recursive && \
    cd zkml-jolt-core && \
    CARGO_NET_GIT_FETCH_WITH_CLI=true cargo build --release && \
    chmod +x ../target/release/zkml-jolt-core && \
    ls -lh ../target/release/zkml-jolt-core && \
    echo "zkML binary built successfully with MAX_TENSOR_SIZE=1024"

# Rewrite existing ONNX to remove ZipMap (non-tensor outputs) for Node compatibility
# Strict: fail build if this step fails so we don't deploy unsupported model shapes
RUN python3 model/strip_zipmap.py

# Expose port
EXPOSE 3000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:3000/health || exit 1

# Clear Python bytecode cache and start
CMD ["sh", "-c", "find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true && find . -type f -name '*.pyc' -delete 2>/dev/null || true && PYTHONDONTWRITEBYTECODE=1 node api/server.js"]
