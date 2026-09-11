#!/bin/bash
# Start script for development (uses Docker)

echo "🐳 Starting application with Docker..."
echo ""

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Error: Docker is not running!"
    echo "Please start Docker Desktop and try again."
    exit 1
fi

# Navigate to project root
cd "$(dirname "$0")/.."

# Start all services
docker-compose up --build

echo ""
echo "✅ Application stopped"
