@echo off
echo ========================================
echo Testing Enhanced Agricultural AI Platform
echo ========================================
echo.

cd /d C:\AI\agri_advisory_app

echo Activating virtual environment...
call venv\Scripts\activate

echo.
echo Running verification script...
python final_verification.py

echo.
echo ========================================
echo Testing API Endpoints...
echo ========================================

echo.
echo Testing Chatbot API with English...
curl -X POST http://127.0.0.1:8000/api/advisory/chatbot/ -H "Content-Type: application/json" -d "{\"query\": \"Hello, I need help with my rice crop\", \"language\": \"en\", \"user_id\": \"test_user\"}"

echo.
echo.
echo Testing Chatbot API with Hindi...
curl -X POST http://127.0.0.1:8000/api/advisory/chatbot/ -H "Content-Type: application/json" -d "{\"query\": \"मुझे चावल की खेती के बारे में सलाह चाहिए\", \"language\": \"hi\", \"user_id\": \"test_farmer\"}"

echo.
echo.
echo Testing Weather API...
curl http://127.0.0.1:8000/api/advisory/weather/?lat=28.6139&lon=77.2090

echo.
echo.
echo Testing Market Prices API...
curl http://127.0.0.1:8000/api/advisory/market-prices/

echo.
echo ========================================
echo Testing Complete!
echo ========================================
echo.
echo If you see JSON responses above, your platform is working correctly!
echo.
pause
