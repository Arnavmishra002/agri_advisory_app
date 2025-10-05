@echo off
echo 🌾 Starting Krishimitra - Farmer-Friendly Agricultural AI Assistant
echo ================================================================
echo.

echo 🚀 Navigating to project directory...
cd /d "%~dp0"

echo 💡 Activating virtual environment...
call venv\Scripts\activate

echo 🔧 Starting Django server in background...
start "Django Server" cmd /k "cd /d "%~dp0" && call venv\Scripts\activate && python manage.py runserver 127.0.0.1:8000"

echo ⏳ Waiting 10 seconds for Django server to start...
timeout /t 10 /nobreak > NUL

echo 🎯 Starting Farmer-Friendly Streamlit App...
start "Farmer-Friendly App" cmd /k "cd /d "%~dp0" && call venv\Scripts\activate && streamlit run streamlit_farmer_friendly.py --server.port 8501 --server.address 127.0.0.1"

echo.
echo 🎉 Farmer-Friendly Agricultural AI Assistant is starting!
echo.
echo 🌐 Django API: http://127.0.0.1:8000
echo 🌐 Streamlit UI: http://127.0.0.1:8501
echo.
echo 🌟 Enhanced Features:
echo    ✅ Voice input with working send button
echo    ✅ Location-specific crop recommendations
echo    ✅ Real government data integration
echo    ✅ Farmer-friendly UI design
echo    ✅ Removed government copyright
echo    ✅ Hindi/English full translation
echo    ✅ Auto location detection
echo    ✅ Real-time weather data
echo    ✅ Market prices from Agmarknet
echo    ✅ Government schemes integration
echo    ✅ Text-to-speech responses
echo.
echo 🎯 Open http://127.0.0.1:8501 in your browser to start!
echo.
echo Press any key to exit this window...
pause > NUL
