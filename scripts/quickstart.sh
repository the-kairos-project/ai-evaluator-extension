#!/bin/bash

# MCP Server Quick Start Script

set -e

echo "🚀 MCP Server Quick Start"
echo "========================"

# Check for required tools
echo "Checking prerequisites..."

if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed. Please install Python 3.11 or higher."
    exit 1
fi

if ! command -v poetry &> /dev/null; then
    echo "❌ Poetry is not installed. Installing..."
    curl -sSL https://install.python-poetry.org | python3 -
    export PATH="$HOME/.local/bin:$PATH"
fi

if ! command -v docker &> /dev/null; then
    echo "⚠️  Docker is not installed. You can still run locally with Python."
fi

# Create .env file if it doesn't exist
if [ ! -f .env ]; then
    echo "Creating .env file..."
    cp example.env .env
    echo "⚠️  Please edit .env and add your OPENAI_API_KEY"
fi

# Install dependencies
echo "Installing dependencies..."
poetry install

# Create directories
echo "Creating directories..."
mkdir -p logs data

echo ""
echo "✅ Setup complete!"
echo ""
echo "Next steps:"
echo "1. Edit .env and add your OPENAI_API_KEY"
echo "2. Run the server:"
echo "   - Local: make run"
echo "   - Docker: make docker-up"
echo "3. Access the API at http://localhost:8000"
echo "4. View docs at http://localhost:8000/docs (dev mode)"
echo ""
echo "Default credentials:"
echo "   Admin: admin/admin123"
echo "   User: user/user123" 