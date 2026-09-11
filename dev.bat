@echo off
REM Start development environment with hot-reload

echo.
echo ========================================
echo   Starting Development Environment
echo ========================================
echo.

REM Check if Docker is running
docker info >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Docker is not running!
    echo Please start Docker Desktop and try again.
    pause
    exit /b 1
)

echo Starting services with hot-reload enabled...
echo.
echo Services will be available at:
echo   - Backend API:      http://localhost:8000
echo   - Backend Docs:     http://localhost:8000/docs
echo   - Frontend (dev):   http://localhost:4200  (with hot-reload)
echo   - Frontend (prod):  http://localhost:80
echo   - Parser Service:   http://localhost:8001
echo   - Database:         localhost:5432
echo.
echo Your code changes will automatically reload!
echo.

REM Start services
docker-compose -f docker-compose.dev.yml up --build

echo.
echo Development environment stopped
pause
