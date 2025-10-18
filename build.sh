#!/bin/bash

# Build script for Render deployment

echo "Starting build process..."
echo "Python version: $(python --version)"
echo "Pip version: $(pip --version)"

# Force Python 3.11 usage and binary wheels
export PYTHON_VERSION=3.11.8
export PIP_PREFER_BINARY=1
export PIP_ONLY_BINARY=":all:"

# Check if we're using the wrong Python version
PYTHON_MAJOR_MINOR=$(python -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
if [ "$PYTHON_MAJOR_MINOR" != "3.11" ]; then
    echo "WARNING: Using Python $PYTHON_MAJOR_MINOR instead of 3.11 - this may cause build issues"
    echo "Attempting to use pre-built wheels only to avoid compilation..."
fi

# Upgrade pip and install build tools
python -m pip install --upgrade pip setuptools wheel

# Strategy: Install packages individually with wheel-only approach
echo "Installing packages with wheels-only strategy to avoid compilation..."

# Install core numerical packages first
echo "Step 1: Installing core numerical libraries..."
python -m pip install numpy --no-cache-dir --only-binary=:all:
python -m pip install pandas --no-cache-dir --only-binary=:all:

# Try to install scipy with different strategies
echo "Step 2: Installing scipy (critical package)..."
echo "Trying latest scipy with wheels..."
python -m pip install "scipy>=1.11.0,<1.14.0" --no-cache-dir --only-binary=:all: || {
    echo "Latest scipy failed, trying specific versions..."
    python -m pip install scipy==1.12.0 --no-cache-dir --only-binary=:all: || \
    python -m pip install scipy==1.11.4 --no-cache-dir --only-binary=:all: || \
    python -m pip install scipy==1.11.3 --no-cache-dir --only-binary=:all: || \
    python -m pip install scipy==1.11.2 --no-cache-dir --only-binary=:all: || {
        echo "All scipy wheel versions failed. Installing without scipy dependency check..."
        python -m pip install scipy --no-cache-dir --prefer-binary --no-build-isolation || {
            echo "WARNING: scipy installation failed. Some ML models may not work."
        }
    }
}

# Install ML packages
echo "Step 3: Installing ML libraries..."
python -m pip install scikit-learn --no-cache-dir --only-binary=:all:
python -m pip install tensorflow==2.20.0 --no-cache-dir --only-binary=:all:
python -m pip install xgboost --no-cache-dir --only-binary=:all:
python -m pip install lightgbm --no-cache-dir --only-binary=:all:

# Install statsmodels after scipy
echo "Step 4: Installing statsmodels..."
python -m pip install statsmodels --no-cache-dir --only-binary=:all: || {
    echo "WARNING: statsmodels installation failed. ARIMA models may not work."
}

# Install remaining packages from requirements
echo "Step 5: Installing remaining packages..."
python -m pip install fastapi uvicorn slowapi --no-cache-dir --only-binary=:all:
python -m pip install motor pymongo requests yfinance --no-cache-dir --only-binary=:all:
python -m pip install pydantic python-dotenv --no-cache-dir --only-binary=:all:
python -m pip install matplotlib seaborn plotly --no-cache-dir --only-binary=:all:

# Final attempt to install any missing packages
echo "Step 6: Final installation attempt..."
python -m pip install -r requirements.txt --no-cache-dir --prefer-binary --no-deps

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
