# 🌿 KrishiMitra AI - Streamlit Frontend

A bilingual, multi-agent AI assistant for farmers built with Streamlit, providing real-time crop price data, localized weather forecasts, and instant plant disease diagnosis.

## ✨ Features

### 🤖 Bilingual Chat Agent
- **Hindi/English Support**: Fully functional in both languages
- **Contextual Responses**: AI-powered responses based on location and farming context
- **Real-time Communication**: Instant responses to farming queries

### 🔬 Pest & Disease Detection
- **Image Upload**: Upload plant leaf images for instant analysis
- **AI Diagnosis**: Get disease detection with confidence scores
- **Treatment Suggestions**: Receive actionable treatment recommendations

### 🌦️ Weather Forecast Agent
- **Real-time Weather**: Current weather conditions for your location
- **7-Day Forecast**: Extended weather predictions
- **Interactive Charts**: Visual weather trend analysis

### 📈 Market Price Agent
- **Live Prices**: Real-time market prices for agricultural commodities
- **Price Trends**: Historical price analysis with interactive charts
- **Location-based**: Prices specific to your region

### 🏠 Dashboard
- **Real-time Data**: Live weather, market prices, and crop recommendations
- **Location Settings**: Easy location switching with quick presets
- **Responsive Design**: Works on desktop and mobile devices

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- Django backend running on port 8000

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/Arnavmishra002/agri_advisory_app
   cd agri_advisory_app
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   venv\Scripts\activate  # Windows
   # or
   source venv/bin/activate  # Linux/Mac
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Start the application**
   
   **Option 1: One-click startup (Windows)**
   ```bash
   start_streamlit.bat
   ```
   
   **Option 2: Manual startup**
   ```bash
   # Terminal 1: Start Django backend
   python manage.py runserver 8000
   
   # Terminal 2: Start Streamlit frontend
   streamlit run streamlit_app.py
   ```

5. **Access the application**
   - Streamlit Frontend: http://localhost:8501
   - Django API: http://localhost:8000

## 🎯 Usage Guide

### Home Dashboard
- View real-time weather data
- Check current market prices
- Get crop recommendations
- Monitor system status

### Chat Agent
1. Select your preferred language (Hindi/English)
2. Type your farming-related questions
3. Get instant AI-powered responses
4. Clear chat history when needed

### Pest Detection
1. Upload a clear image of a plant leaf
2. Click "Analyze Image"
3. Get disease diagnosis and treatment suggestions
4. View confidence scores

### Weather Agent
1. Set your location in the sidebar
2. View current weather conditions
3. Check 7-day forecast
4. Analyze weather trends

### Market Prices
1. View current commodity prices
2. Analyze price trends
3. Get location-specific pricing
4. Monitor market fluctuations

## 🛠️ Technical Details

### Architecture
- **Frontend**: Streamlit
- **Backend**: Django REST API
- **AI/ML**: TensorFlow, scikit-learn
- **Visualization**: Plotly
- **Image Processing**: PIL/Pillow

### API Integration
The Streamlit frontend integrates with the Django backend through REST APIs:
- `/api/weather/current/` - Weather data
- `/api/market-prices/prices/` - Market prices
- `/api/advisories/chatbot/` - Chat responses
- `/api/advisories/pest_detection/` - Disease detection
- `/api/advisories/ml_crop_recommendation/` - Crop recommendations

### Language Support
- **Hindi**: Full interface support
- **English**: Complete functionality
- **Regional Languages**: Bengali, Telugu, Marathi (planned)

## 🎨 Customization

### Styling
The app uses custom CSS for a farming-themed design:
- Green color scheme (#2d5016, #4a7c59)
- Card-based layout
- Responsive design
- Mobile-friendly interface

### Configuration
- Language settings in sidebar
- Location configuration
- API endpoint configuration in code

## 📱 Mobile Support

The Streamlit app is fully responsive and works on:
- Desktop browsers
- Mobile phones
- Tablets
- Touch devices

## 🔧 Troubleshooting

### Common Issues

1. **API Connection Error**
   - Ensure Django backend is running on port 8000
   - Check network connectivity
   - Verify API endpoints

2. **Image Upload Issues**
   - Use supported formats: JPG, JPEG, PNG
   - Ensure image size is reasonable (< 10MB)
   - Check image clarity

3. **Language Switching**
   - Clear browser cache if language doesn't change
   - Refresh the page after language selection

### Performance Tips
- Use smaller images for faster processing
- Clear chat history regularly
- Close unused browser tabs

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments

- **IBM SkillsBuild** for inspiration
- **Streamlit** for the amazing framework
- **Django** for robust backend
- **TensorFlow** for AI capabilities
- **Plotly** for beautiful visualizations

## 📞 Support

For support and questions:
- Create an issue on GitHub
- Contact the development team
- Check the documentation

---

**🌿 KrishiMitra AI - Empowering Farmers with Technology**
