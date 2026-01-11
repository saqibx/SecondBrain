#!/bin/bash
# SecondBrain Setup Script
# Run this script to set up SecondBrain for development

set -e  # Exit on error

echo "========================================"
echo "SecondBrain Development Setup"
echo "========================================"
echo ""

# Check Python version
echo "Checking Python installation..."
python_version=$(python3 --version 2>&1)
echo "✓ Found: $python_version"

# Check if virtual environment exists
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
pip install --upgrade pip setuptools wheel

# Install dependencies
echo "Installing Python dependencies..."
pip install -r requirements.txt

# Check for .env file
if [ ! -f ".env" ]; then
    echo ""
    echo "⚠️  No .env file found!"
    echo "Creating .env from .env.example..."
    cp .env.example .env
    echo "✓ .env created - please edit it with your API keys"
    echo ""
    echo "Required environment variables:"
    echo "  - OPENAI_API_KEY: Get from https://platform.openai.com/api-keys"
    echo "  - TAVILY_API_KEY: Get from https://tavily.com"
    echo "  - APP_SECRET_KEY: Use a strong random key"
    echo ""
else
    echo "✓ .env file exists"
fi

# Create necessary directories
echo "Creating necessary directories..."
mkdir -p logs DATA Classes/chroma_db

# Check MongoDB
echo ""
echo "Checking MongoDB..."
if command -v mongod &> /dev/null; then
    echo "✓ MongoDB found"
    if ! pgrep mongod > /dev/null; then
        echo "  ⚠️  MongoDB not running"
        echo "  Start with: brew services start mongodb-community"
    else
        echo "  ✓ MongoDB is running"
    fi
else
    echo "  ⚠️  MongoDB not installed"
    echo "  Install with: brew install mongodb-community"
fi

# Check Redis
echo "Checking Redis..."
if command -v redis-server &> /dev/null; then
    echo "✓ Redis found"
    if ! pgrep redis-server > /dev/null; then
        echo "  ⚠️  Redis not running"
        echo "  Start with: brew services start redis"
    else
        echo "  ✓ Redis is running"
    fi
else
    echo "  ⚠️  Redis not installed"
    echo "  Install with: brew install redis"
fi

echo ""
echo "========================================"
echo "Setup Complete! ✓"
echo "========================================"
echo ""
echo "Next steps:"
echo "1. Edit .env file with your API keys"
echo "2. Start MongoDB: brew services start mongodb-community"
echo "3. Start Redis: brew services start redis"
echo "4. Run the app: python app.py"
echo ""
echo "Or use Docker Compose:"
echo "  docker-compose up --build"
echo ""
