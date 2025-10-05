@echo off
echo ========================================
echo Enhanced Agri Advisory App - Full Setup
echo ========================================
echo.

REM Navigate to project directory
cd /d C:\AI\agri_advisory_app

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python 3.8+ and try again
    pause
    exit /b 1
)

REM Create virtual environment if it doesn't exist
if not exist "venv" (
    echo Creating virtual environment...
    python -m venv venv
    if errorlevel 1 (
        echo ERROR: Failed to create virtual environment
        pause
        exit /b 1
    )
)

REM Activate virtual environment
echo Activating virtual environment...
call venv\Scripts\activate.bat
if errorlevel 1 (
    echo ERROR: Failed to activate virtual environment
    pause
    exit /b 1
)

REM Install dependencies
echo Installing dependencies...
pip install --upgrade pip
pip install -r requirements_basic.txt
if errorlevel 1 (
    echo ERROR: Failed to install dependencies
    pause
    exit /b 1
)

REM Create migrations
echo Creating database migrations...
python manage.py makemigrations advisory
if errorlevel 1 (
    echo ERROR: Failed to create migrations
    pause
    exit /b 1
)

REM Apply migrations
echo Running database migrations...
python manage.py migrate
if errorlevel 1 (
    echo ERROR: Failed to apply migrations
    pause
    exit /b 1
)

REM Create superuser if it doesn't exist
echo Checking for admin user...
python manage.py shell -c "from django.contrib.auth.models import User; User.objects.filter(username='admin').exists() or User.objects.create_superuser('admin', 'admin@example.com', 'admin123')"

REM Start the application
echo.
echo ========================================
echo Enhanced Agri Advisory App Ready!
echo ========================================
echo.
echo Features Available:
echo - ChatGPT-like Multilingual Chatbot (25+ languages)
echo - Persistent Chat History across sessions
echo - Advanced AI Conversations
echo - Agricultural Expertise and Recommendations
echo - Real-time Weather and Market Data
echo - Voice Support (TTS)
echo - Community Forum
echo.
echo Access Points:
echo - Main Application: http://localhost:8000/
echo - API Endpoints: http://localhost:8000/api/
echo - Interactive API Docs: http://localhost:8000/api/schema/swagger-ui/
echo - Admin Panel: http://localhost:8000/admin/
echo.
echo Admin Credentials:
echo - Username: admin
echo - Password: admin123
echo.
echo Test Your Chatbot:
echo 1. Open browser to http://localhost:8000/api/schema/swagger-ui/
echo 2. Try the /api/advisories/chatbot/ endpoint
echo 3. Test with different languages (en, hi, bn, te, ta, etc.)
echo 4. Use the test_chatbot.bat file for automated testing
echo.
echo Press Ctrl+C to stop the server
echo ========================================
echo.

python manage.py runserver 127.0.0.1:8000
