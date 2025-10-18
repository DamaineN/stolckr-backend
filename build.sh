#!/bin/bash

# Build script for Render deployment

echo "Starting build process..."

# Set Python to use specific version (ignore if system override)
export PYTHON_VERSION=3.11.9

# Upgrade pip and install build tools
python -m pip install --upgrade pip setuptools wheel

# Install dependencies with specific options
python -m pip install -r requirements.txt --no-cache-dir

# Create necessary directories
mkdir -p models/saved
mkdir -p data/cache
mkdir -p logs

echo "Build completed successfully!"
