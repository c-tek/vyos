#!/bin/bash

# Setup script for VyOS API development environment
# Created: June 17, 2025

set -e  # Exit on error

echo "=== VyOS API Development Environment Setup ==="
echo ""

# Check Python version (require 3.8+)
PYTHON_VERSION=$(python3 --version | cut -d ' ' -f 2)
PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d '.' -f 1)
PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d '.' -f 2)

if [ $PYTHON_MAJOR -lt 3 ] || [ $PYTHON_MAJOR -eq 3 -a $PYTHON_MINOR -lt 8 ]; then
    echo "ERROR: Python 3.8+ is required (found $PYTHON_VERSION)"
    echo "Please install a compatible Python version and try again"
    exit 1
fi

echo "✓ Python $PYTHON_VERSION detected"

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
    echo "✓ Virtual environment created"
else
    echo "✓ Virtual environment already exists"
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo "Upgrading pip..."
pip install --upgrade pip

# Install dependencies from fixed requirements
if [ -f "requirements-fixed.txt" ]; then
    echo "Installing dependencies from requirements-fixed.txt..."
    pip install -r requirements-fixed.txt
else
    echo "Installing dependencies from requirements.txt..."
    pip install -r requirements.txt
fi

# Install development dependencies if they exist
if [ -f "requirements-dev.txt" ]; then
    echo "Installing development dependencies..."
    pip install -r requirements-dev.txt
fi

# Setup pre-commit hooks
if command -v pre-commit &> /dev/null; then
    echo "Setting up pre-commit hooks..."
    pre-commit install
fi

# Initialize database if not already done
echo "Setting up database..."
python -m alembic upgrade head

echo ""
echo "=== VyOS API Development Environment Ready ==="
echo ""
echo "To activate the environment, run:"
echo "  source venv/bin/activate"
echo ""
echo "To run the development server:"
echo "  python main.py"
echo ""
echo "Happy coding!"
