# KrishiMitra - AI-Powered Agri-Advisory Platform 🌾

**KrishiMitra** is a next-generation agricultural advisory platform designed to empower Indian farmers with real-time, data-driven insights. By leveraging advanced AI and government APIs, it provides accurate weather forecasts, market prices, crop recommendations, and government scheme information in local languages.

![KrishiMitra Dashboard](https://raw.githubusercontent.com/Arnavmishra002/agri_advisory_app/main/docs/dashboard_preview.png)

## 🚀 Key Features

### 1. 🌦️ Hyper-Local Weather Forecasts
- **Real-time Weather:** Get accurate temperature, humidity, and wind speed data for your specific village or district.
- **7-Day Forecast:** Plan your farming activities with a detailed 7-day weather outlook.
- **Advisories:** Receive timely alerts for rain, storms, or extreme heat.

### 2. 💰 Real-Time Market Prices (Mandi Bhav)
- **Live Data:** Access up-to-date market prices from nearby Mandis (e.g., Azadpur, Ghazipur, Okhla).
- **Profit Analysis:** See calculated profit margins based on MSP and current market rates.
- **Trend Indicators:** Visual indicators (📈/📉) to show if prices are rising or falling.
- **Mandi Selection:** Easily switch between different Mandis to find the best price for your crops.

### 3. 🤖 AI Crop Recommendations
- **Personalized Advice:** Get crop suggestions based on your soil type, season, and local climate.
- **Profitability Score:** Each recommendation includes a projected profitability analysis.
- **Detailed Insights:** Learn about seed varieties, fertilizer requirements, and expected yield.

### 4. 🏛️ Government Schemes
- **Comprehensive List:** Access a database of central and state government schemes (e.g., PM-Kisan).
- **Eligibility Check:** Find out which schemes you are eligible for.
- **Application Guide:** Step-by-step instructions on how to apply.

### 5. 🗣️ Multilingual Support
- **Hindi & English:** Fully localized interface for Hindi and English speakers.
- **Voice Support:** (Coming Soon) Voice-activated commands for easier accessibility.

## 🛠️ Technology Stack

- **Backend:** Django (Python), Django REST Framework
- **Frontend:** HTML5, CSS3, Vanilla JavaScript (Responsive Design)
- **Database:** PostgreSQL (Production), SQLite (Development)
- **AI/ML:** Google Gemini Pro (for intelligent insights), Scikit-Learn (for crop prediction)
- **APIs:** Open-Meteo (Weather), Government Data APIs (Market Prices)
- **Deployment:** Render / Railway

## 📋 Recent Updates (v2.0)

- **✅ Fixed MSP Display:** Corrected Minimum Support Price (MSP) data for fruits and vegetables.
- **✅ Enhanced Weather:** Implemented a full 7-day weather forecast with detailed metrics.
- **✅ Mandi Dropdown Fix:** Resolved issues with Mandi selection to ensure accurate price loading for specific markets like Ghazipur and Okhla.
- **✅ UI Improvements:** Modernized the dashboard with a clean, mobile-friendly design.

## 🚀 Deployment Guide

### Deploying to Render

1.  **Fork/Clone this repository.**
2.  **Create a new Web Service** on [Render](https://render.com/).
3.  **Connect your GitHub repository.**
4.  **Settings:**
    -   **Runtime:** Python 3
    -   **Build Command:** pip install -r requirements.txt && python manage.py collectstatic --noinput && python manage.py migrate
    -   **Start Command:** gunicorn agri_advisory_app.wsgi:application
5.  **Environment Variables:**
    -   PYTHON_VERSION: 3.9.0 (or your preferred version)
    -   SECRET_KEY: (Generate a strong random key)
    -   DEBUG: False
    -   ALLOWED_HOSTS: * (or your specific domain)
    -   DATABASE_URL: (Add your internal/external database URL)

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 📄 License

This project is licensed under the MIT License.
