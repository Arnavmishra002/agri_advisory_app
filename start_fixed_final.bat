@echo off
echo 🌾 Starting Krishimitra - Fixed Final Version
echo ============================================
echo.

echo 🚀 Navigating to project directory...
cd /d "%~dp0"

echo 💡 Activating virtual environment...
call venv\Scripts\activate

echo 🔧 Starting Django server in background...
start "Django Server" cmd /k "cd /d "%~dp0" && call venv\Scripts\activate && python manage.py runserver 127.0.0.1:8000"

echo ⏳ Waiting 15 seconds for Django server to start...
timeout /t 15 /nobreak > NUL

echo 🎯 Starting Fixed Final Streamlit App...
start "Fixed Final App" cmd /k "cd /d "%~dp0" && call venv\Scripts\activate && streamlit run streamlit_fixed_final.py --server.port 8501 --server.address 127.0.0.1"

echo.
echo 🎉 Fixed Final Version is starting!
echo.
echo 🌐 Django API: http://127.0.0.1:8000
echo 🌐 Streamlit UI: http://127.0.0.1:8501
echo.
echo ✅ ALL ISSUES FIXED:
echo    ✅ Weather data N/A values - FIXED with real data
echo    ✅ Voice input like ChatGPT - FIXED with seamless integration
echo    ✅ Real data display - FIXED with live API data
echo    ✅ Manual location input - ADDED
echo    ✅ Translation issues - FIXED
echo    ✅ Server connection - FIXED
echo.
echo 🌟 Features:
echo    ✅ ChatGPT-like voice input with text fallback
echo    ✅ Real weather data based on location
echo    ✅ Location-specific crop recommendations
echo    ✅ Live market prices
echo    ✅ Manual location input option
echo    ✅ Full Hindi/English translation
echo    ✅ Text-to-speech responses
echo    ✅ Beautiful farmer-friendly UI
echo.
echo 🎯 Open http://127.0.0.1:8501 in your browser!
echo.
echo Press any key to exit this window...
pause > NUL
