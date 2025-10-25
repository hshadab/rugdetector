#!/bin/bash
# Clear Python bytecode cache to ensure latest code runs
find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
find . -type f -name '*.pyc' -delete 2>/dev/null || true

# Set environment variable to disable bytecode creation
export PYTHONDONTWRITEBYTECODE=1

# Start the server
node api/server.js
