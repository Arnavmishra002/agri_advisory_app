@echo off
echo Starting Agri Advisory App with Docker...
echo.

REM Navigate to project directory
cd /d C:\AI\agri_advisory_app

echo ========================================
echo Starting with Docker (Recommended)
echo ========================================
echo.
echo This will:
echo 1. Build the Docker containers
echo 2. Start all services automatically
echo 3. Run database migrations
echo.
echo Access the app at: http://localhost:8000/
echo API Documentation: http://localhost:8000/api/schema/swagger-ui/
echo Admin Panel: http://localhost:8000/admin/
echo.
echo Press Ctrl+C to stop all services
echo ========================================
echo.

REM Start with Docker Compose
docker-compose up --build

echo.
echo Docker services stopped.
pause
