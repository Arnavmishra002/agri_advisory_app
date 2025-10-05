@echo off
echo ========================================
echo Starting Enhanced Agri Advisory App
echo with ChatGPT-like Multilingual Chatbot
echo ========================================
echo.

REM Navigate to project directory
cd /d C:\AI\agri_advisory_app

REM Check if virtual environment exists
if not exist "venv" (
    echo Creating virtual environment...
    python -m venv venv
)

REM Activate virtual environment
echo Activating virtual environment...
call venv\Scripts\activate.bat

REM Install/update dependencies
echo Installing dependencies...
pip install -r requirements_basic.txt

REM Create migrations for new chat models
echo Creating database migrations...
python manage.py makemigrations advisory

REM Apply migrations
echo Running database migrations...
python manage.py migrate

REM Start the Django server
echo Starting Django server...
echo.
echo ========================================
echo Enhanced Agri Advisory App Starting...
echo ========================================
echo.
echo Features:
echo - ChatGPT-like Multilingual Chatbot (25+ languages)
echo - Persistent Chat History
echo - Advanced AI Conversations
echo - Agricultural Expertise
echo.
echo Access Points:
echo - Main App: http://localhost:8000/
echo - API: http://localhost:8000/api/
echo - API Docs: http://localhost:8000/api/schema/swagger-ui/
echo - Admin Panel: http://localhost:8000/admin/
echo.
echo Test Commands:
echo - Chat API: POST http://localhost:8000/api/advisories/chatbot/
echo - Weather: GET http://localhost:8000/api/weather/current/?lat=28.6139^&lon=77.2090
echo - Market: GET http://localhost:8000/api/market-prices/prices/?lat=28.6139^&lon=77.2090
echo.
echo Press Ctrl+C to stop the server
echo ========================================
echo.

python manage.py runserver 127.0.0.1:8000
