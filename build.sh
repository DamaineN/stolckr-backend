#!/bin/bash

# Build script for Render deployment

# Upgrade pip and install build tools
pip install --upgrade pip setuptools wheel

# Install dependencies
pip install -r requirements.txt

# Create necessary directories
mkdir -p models/saved
mkdir -p data/cache
mkdir -p logs

echo "Build completed successfully!"