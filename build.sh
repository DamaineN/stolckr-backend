#!/bin/bash

# Build script for Render deployment

echo "Starting build process..."
echo "Python version: $(python --version)"
echo "Pip version: $(pip --version)"

# Set Python to use specific version (ignore if system override)
export PYTHON_VERSION=3.11.8
export PIP_PREFER_BINARY=1

# Upgrade pip and install build tools
python -m pip install --upgrade pip setuptools wheel

# Try to install with binary wheels first, fallback if needed
echo "Installing packages with binary wheels preferred..."
python -m pip install -r requirements.txt --no-cache-dir --prefer-binary

if [ $? -ne 0 ]; then
    echo "Binary installation failed, trying with specific problematic packages..."
    
    # Install core packages first
    echo "Installing core packages..."
    python -m pip install numpy==2.0.2 --no-cache-dir --only-binary=:all: || python -m pip install numpy==1.26.4 --no-cache-dir
    python -m pip install pandas==2.2.3 --no-cache-dir --only-binary=:all:
    
    # Try scipy with fallback
    echo "Installing scipy..."
    python -m pip install scipy==1.13.1 --no-cache-dir --only-binary=:all: || python -m pip install scipy==1.11.3 --no-cache-dir --only-binary=:all:
    
    # Install remaining packages
    echo "Installing remaining packages..."
    python -m pip install -r requirements.txt --no-cache-dir --prefer-binary
fi

# Create necessary directories
mkdir -p models/saved
mkdir -p models/ensemble/saved_models
mkdir -p models/lstm/saved_models 
mkdir -p models/arima/saved_models
mkdir -p data/cache
mkdir -p logs

echo "Verifying installation..."
python -c "import tensorflow, numpy, pandas, scipy, sklearn; print('Core ML packages imported successfully')"

echo "Build completed successfully!"
