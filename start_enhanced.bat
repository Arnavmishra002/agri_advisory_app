@echo off
echo 🌾 Starting Krishimitra Enhanced Agricultural AI Assistant
echo ================================================================
echo.

echo 🚀 Navigating to project directory...
cd /d "%~dp0"

echo 📍 Current directory: %CD%

echo 💡 Activating virtual environment...
call venv\Scripts\activate

echo 📦 Installing/Updating dependencies...
pip install -r requirements.txt

echo ⚙️ Starting Django server...
start "Django Server" cmd /k "cd /d "%~dp0" && call venv\Scripts\activate && echo Starting Django server... && python manage.py runserver 127.0.0.1:8000"

echo ⏳ Waiting 15 seconds for Django server to start...
timeout /t 15 /nobreak > NUL

echo 🧪 Testing API endpoints...
python quick_test.py

echo.
echo 🌐 Starting Enhanced Streamlit app with Voice Input...
start "Enhanced Streamlit App" cmd /k "cd /d "%~dp0" && call venv\Scripts\activate && echo Starting Enhanced Streamlit... && streamlit run streamlit_final.py --server.port 8501 --server.address 127.0.0.1"

echo.
echo ✅ Both servers are starting!
echo.
echo 🔗 Django API: http://127.0.0.1:8000
echo 🔗 Enhanced Streamlit UI: http://127.0.0.1:8501
echo.
echo 🎯 Enhanced Features:
echo    ✅ Real Government APIs (IMD, Agmarknet, ICAR)
echo    ✅ Voice Input with Speech Recognition
echo    ✅ Full Page Translation (Hindi/English)
echo    ✅ Language Selection Popup
echo    ✅ Real-time Crop Prices and Trending Crops
echo    ✅ AI/ML Powered Recommendations
echo    ✅ ChatGPT-like Conversations
echo    ✅ Government Website Style Interface
echo.
echo 🎤 Voice Input Requirements:
echo    - Microphone access permission
echo    - Internet connection for speech recognition
echo    - Supported browsers: Chrome, Edge, Firefox
echo.
echo Press any key to exit this window...
pause > NUL
