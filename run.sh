#!/bin/bash
set -e

echo "AIODarr - AIOStreams-Radarr Bridge"
echo "=================================="

# Check if .env exists
if [ ! -f .env ]; then
    echo "Error: .env file not found"
    echo "Please copy .env.example to .env and configure it"
    exit 1
fi

# Check if uv is installed
if ! command -v uv &> /dev/null; then
    echo "Error: uv is not installed"
    echo "Install it with: curl -LsSf https://astral.sh/uv/install.sh | sh"
    exit 1
fi

# Install/sync dependencies
echo "Installing dependencies with uv..."
uv sync

# Run the service
echo "Starting service..."
uv run python -m src.main
