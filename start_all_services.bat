@echo off
echo Starting All Agri Advisory App Services...
echo.

REM Navigate to project directory
cd /d C:\AI\agri_advisory_app

REM Activate virtual environment
echo Activating virtual environment...
call venv\Scripts\activate.bat

REM Install dependencies
echo Installing dependencies...
pip install -r requirements.txt

REM Run migrations
echo Running database migrations...
python manage.py makemigrations advisory
python manage.py migrate

echo.
echo ========================================
echo Starting All Services...
echo ========================================
echo.
echo This will start:
echo 1. Django Server (Main App)
echo 2. Celery Worker (Background Tasks)
echo 3. Celery Beat (Scheduled Tasks)
echo.
echo Access the app at: http://localhost:8000/
echo API Documentation: http://localhost:8000/api/schema/swagger-ui/
echo Admin Panel: http://localhost:8000/admin/
echo.
echo Press Ctrl+C to stop all services
echo ========================================
echo.

REM Start all services in background
start "Django Server" cmd /k "call venv\Scripts\activate.bat && python manage.py runserver"
timeout /t 3 /nobreak >nul

start "Celery Worker" cmd /k "call venv\Scripts\activate.bat && celery -A core worker --loglevel=info"
timeout /t 2 /nobreak >nul

start "Celery Beat" cmd /k "call venv\Scripts\activate.bat && celery -A core beat --loglevel=info"

echo.
echo All services are starting in separate windows...
echo Check the opened windows for any errors.
echo.
echo Press any key to exit this launcher...
pause >nul
