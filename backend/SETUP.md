# Backend Setup Guide

## Quick Start (RECOMMENDED)

### Option 1: Using Docker (Works on All Platforms) 🐳

**This is the easiest and most reliable method!**

```bash
# Start all services (backend, database, frontend)
docker-compose up --build
```

The backend will be available at: `http://localhost:8000`

**Advantages:**
- ✅ Works identically on Windows, macOS, and Linux
- ✅ No need to install Python dependencies locally
- ✅ Includes PostgreSQL database automatically
- ✅ No compilation issues

---

## Option 2: Local Installation

### Prerequisites

- Python 3.11+
- Virtual environment created at `../.venv311`

### Installation Steps

#### On Windows:

**Method A: Using the install script (Recommended)**
```bash
cd backend
bash install.sh
```

**Method B: If compilation issues occur**
1. Install [Docker Desktop](https://www.docker.com/products/docker-desktop) and use Option 1 above
2. OR install [Visual Studio Build Tools](https://visualstudio.microsoft.com/downloads/) with "Desktop development with C++"
3. Then run:
```bash
cd backend
cmd.exe //c install_requirements.bat
```

#### On macOS:

```bash
cd backend

# Install Xcode Command Line Tools if needed
xcode-select --install

# Run install script
bash install.sh
```

#### On Linux (Ubuntu/Debian):

```bash
cd backend

# Install build tools if needed
sudo apt-get update
sudo apt-get install -y build-essential python3-dev

# Run install script
bash install.sh
```

---

## Running the Backend Locally

```bash
cd backend

# Activate virtual environment
source ../.venv311/Scripts/activate  # Windows (Git Bash)
source ../.venv311/bin/activate      # macOS/Linux

# Start the server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

---

## Troubleshooting

### "Failed building wheel for ckzg" on Windows

This happens because the `ckzg` package (required by `web3`) needs C++ compilation.

**Solution:** Use Docker (Option 1 above) - this avoids all compilation issues!

### Port Already in Use

```bash
# Find and kill process using port 8000
# Windows:
netstat -ano | findstr :8000
taskkill /PID <PID> /F

# macOS/Linux:
lsof -ti:8000 | xargs kill -9
```

### Virtual Environment Not Found

```bash
# Create virtual environment first
cd ..
python -m venv .venv311
cd backend
```

---

## Environment Variables

Create a `.env` file in the project root (see `.env.example`):

```env
# Database
POSTGRES_USER=your_user
POSTGRES_PASSWORD=your_password
POSTGRES_DB=your_database
DATABASE_URL=postgresql://user:password@localhost:5432/dbname

# JWT
SECRET_KEY=your_secret_key
ALGORITHM=HS256

# Add other required variables...
```

---

## Why Docker is Recommended

1. **Cross-platform consistency**: Same behavior on all operating systems
2. **No compilation issues**: Pre-built Linux environment handles all dependencies
3. **Isolated environment**: Doesn't interfere with your system Python
4. **Easy deployment**: Same Docker setup works in production
5. **Includes database**: PostgreSQL runs automatically

**Bottom line:** Docker eliminates 99% of setup issues! 🎉
