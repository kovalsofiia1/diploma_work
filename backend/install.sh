#!/bin/bash
# Cross-platform installation script for backend dependencies

set -e

echo "🚀 Backend Installation Script"
echo "================================"
echo ""

# Detect OS
if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" ]]; then
    OS="windows"
elif [[ "$OSTYPE" == "darwin"* ]]; then
    OS="mac"
else
    OS="linux"
fi

echo "📍 Detected OS: $OS"
echo ""

# Check if virtual environment exists
if [ ! -d "../.venv311" ]; then
    echo "❌ Virtual environment not found at ../.venv311"
    echo "Please create it first:"
    echo "  python -m venv ../.venv311"
    exit 1
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
if [ "$OS" = "windows" ]; then
    source ../.venv311/Scripts/activate
else
    source ../.venv311/bin/activate
fi

# Upgrade pip
echo "📦 Upgrading pip..."
pip install --upgrade pip setuptools wheel

# Try to install requirements
echo ""
echo "📥 Installing Python packages..."
echo ""

if pip install -r requirements.txt; then
    echo ""
    echo "✅ Installation completed successfully!"
    echo ""
    echo "🎉 You can now start the backend:"
    echo "   cd backend"
    if [ "$OS" = "windows" ]; then
        echo "   source ../.venv311/Scripts/activate"
    else
        echo "   source ../.venv311/bin/activate"
    fi
    echo "   uvicorn app.main:app --reload"
else
    echo ""
    echo "⚠️  Installation failed!"
    echo ""
    
    if [ "$OS" = "windows" ]; then
        echo "Windows users: Some packages require C++ compilation."
        echo ""
        echo "Option 1 (RECOMMENDED): Use Docker"
        echo "  1. Install Docker Desktop: https://www.docker.com/products/docker-desktop"
        echo "  2. Run: docker-compose up"
        echo ""
        echo "Option 2: Install Visual Studio Build Tools"
        echo "  1. Download from: https://visualstudio.microsoft.com/downloads/"
        echo "  2. Install 'Desktop development with C++'"
        echo "  3. Run: cmd.exe //c install_requirements.bat"
        echo ""
    else
        echo "Please ensure you have the required build tools:"
        echo "  - GCC/G++ compiler"
        echo "  - Python development headers"
        echo ""
        echo "On Ubuntu/Debian: sudo apt-get install build-essential python3-dev"
        echo "On macOS: xcode-select --install"
    fi
    
    exit 1
fi
