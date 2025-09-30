@echo off
echo Starting Agri Advisory App...
echo.

REM Navigate to project directory
cd /d C:\Users\RITESH RANA\agri_advisory_app

REM Activate virtual environment
echo Activating virtual environment...
call venv\Scripts\activate.bat

REM Ensure basic migrations are applied
echo Running database migrations...
python manage.py migrate

REM Start the Django server
echo Starting Django server...
echo.
echo ========================================
echo Agri Advisory App is starting...
echo ========================================
echo.
echo Access the app at: http://localhost:8000/
echo API Documentation: http://localhost:8000/api/schema/swagger-ui/
echo Admin Panel: http://localhost:8000/admin/
echo.
echo Press Ctrl+C to stop the server
echo ========================================
echo.

python manage.py runserver 127.0.0.1:8000
