@echo off
echo Starting Celery Beat Scheduler...
echo.

REM Navigate to project directory
cd /d C:\AI\agri_advisory_app

REM Activate virtual environment
echo Activating virtual environment...
call venv\Scripts\activate.bat

REM Start Celery beat
echo Starting Celery beat scheduler...
echo.
echo ========================================
echo Celery Beat Scheduler is starting...
echo ========================================
echo.
echo This handles scheduled tasks (weather updates, etc.)
echo Keep this window open while using the app
echo.
echo Press Ctrl+C to stop the scheduler
echo ========================================
echo.

celery -A core beat --loglevel=info
