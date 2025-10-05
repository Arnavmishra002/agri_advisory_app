@echo off
echo 🌾 Starting Krishimitra Agricultural AI Assistant - COMPLETE SETUP
echo =================================================================
echo.

echo 🚀 Navigating to project directory...
cd /d "%~dp0"

echo 💡 Activating virtual environment...
call venv\Scripts\activate

echo ⚙️ Starting Django server in background...
start "Django Server" cmd /k "cd /d "%~dp0" && call venv\Scripts\activate && python manage.py runserver 127.0.0.1:8000"

echo ⏳ Waiting 10 seconds for Django server to start...
timeout /t 10 /nobreak > NUL

echo 🧪 Testing API endpoints...
python quick_test.py

echo.
echo 🌐 Starting Streamlit app...
start "Streamlit App" cmd /k "cd /d "%~dp0" && call venv\Scripts\activate && streamlit run streamlit_final.py --server.port 8501 --server.address 127.0.0.1"

echo.
echo ✅ Both servers are starting!
echo.
echo 🔗 Django API: http://127.0.0.1:8000
echo 🔗 Streamlit UI: http://127.0.0.1:8501
echo.
echo 🎯 All features should now work:
echo    ✅ Chatbot with ICAR-based crop recommendations
echo    ✅ Weather data with real-time information
echo    ✅ Trending crops with descriptions and benefits
echo    ✅ Market prices with price cards and analysis
echo    ✅ Agricultural advisory with government schemes
echo    ✅ Multi-language support (Hindi/English/Hinglish)
echo    ✅ Fixed price trend charts
echo.
echo Press any key to exit this window...
pause > NUL