# Krishimitra AI - Intelligent Agricultural Advisory System

![Krishimitra AI](https://img.shields.io/badge/Krishimitra-AI-green)
![Django](https://img.shields.io/badge/Django-5.2.6-blue)
![Python](https://img.shields.io/badge/Python-3.11-yellow)
![License](https://img.shields.io/badge/License-MIT-red)

## 🌾 Overview

Krishimitra AI is an intelligent agricultural advisory system that provides real-time farming guidance, crop recommendations, weather forecasts, market prices, government schemes, and pest detection using advanced AI technology and government APIs.

## ✨ Features

### 🤖 AI-Powered Assistant
- **Smart Query Routing**: Automatically routes farming queries to government APIs and general queries to Ollama
- **ChatGPT-like Responses**: Natural, conversational AI with context awareness
- **Multilingual Support**: Hindi, English, and Hinglish support
- **Real-time Processing**: Instant responses with government data integration

### 🌾 Agricultural Services
- **Crop Recommendations**: Location-specific crop suggestions with profit analysis
- **Weather Data**: Real-time weather information from IMD
- **Market Prices**: Live mandi prices and MSP information
- **Government Schemes**: Comprehensive scheme information and eligibility
- **Pest Detection**: Image-based disease analysis and solutions

### 📍 Location Services
- **GPS Detection**: Automatic location detection
- **Manual Search**: Search for any Indian location
- **Reverse Geocoding**: Coordinate to location conversion
- **Dynamic Updates**: All services update based on location

### 🏛️ Government API Integration
- **IMD Weather**: Indian Meteorological Department data
- **ICAR**: Indian Council of Agricultural Research
- **Agmarknet**: Agricultural marketing data
- **e-NAM**: National Agricultural Market
- **PM-Kisan**: Government scheme data

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- PostgreSQL 15+
- Redis 7+
- Ollama (for AI responses)

### Installation

1. **Clone the repository**
```bash
git clone https://github.com/yourusername/krishimitra-ai.git
cd krishimitra-ai
```

2. **Create virtual environment**
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies**
```bash
pip install -r requirements.txt
```

4. **Set up environment variables**
```bash
cp .env.example .env
# Edit .env with your configuration
```

5. **Set up database**
```bash
python manage.py migrate
python manage.py createsuperuser
```

6. **Collect static files**
```bash
python manage.py collectstatic
```

7. **Run the server**
```bash
python manage.py runserver
```

Visit `http://127.0.0.1:8000/` to access the application.

## 🐳 Docker Deployment

### Using Docker Compose

1. **Clone and navigate to project**
```bash
git clone https://github.com/yourusername/krishimitra-ai.git
cd krishimitra-ai
```

2. **Start all services**
```bash
docker-compose up -d
```

3. **Run migrations**
```bash
docker-compose exec web python manage.py migrate
```

4. **Create superuser**
```bash
docker-compose exec web python manage.py createsuperuser
```

5. **Access the application**
- Web: `http://localhost:8000`
- Admin: `http://localhost:8000/admin`

### Using Docker

1. **Build the image**
```bash
docker build -t krishimitra-ai .
```

2. **Run the container**
```bash
docker run -p 8000:8000 krishimitra-ai
```

## ☁️ Render Deployment

### Deploy to Render.com

1. **Fork this repository**
2. **Connect to Render**
   - Go to [Render.com](https://render.com)
   - Connect your GitHub account
   - Create a new Web Service

3. **Configure deployment**
   - **Build Command**: `pip install -r requirements.txt && python manage.py collectstatic --noinput`
   - **Start Command**: `gunicorn agri_advisory_app.wsgi:application`
   - **Python Version**: 3.11

4. **Set environment variables**
   ```
   DJANGO_SETTINGS_MODULE=agri_advisory_app.settings.production
   SECRET_KEY=your-secret-key-here
   DEBUG=False
   ALLOWED_HOSTS=your-app-name.onrender.com
   DATABASE_URL=postgresql://user:password@host:port/database
   REDIS_URL=redis://user:password@host:port
   ```

5. **Deploy**
   - Click "Deploy" and wait for deployment to complete
   - Your app will be available at `https://your-app-name.onrender.com`

## 🔧 Configuration

### Environment Variables

Create a `.env` file with the following variables:

```env
# Django Settings
SECRET_KEY=your-secret-key-here
DEBUG=False
ALLOWED_HOSTS=localhost,127.0.0.1,your-domain.com

# Database
DATABASE_URL=postgresql://user:password@host:port/database

# Redis
REDIS_URL=redis://localhost:6379/0

# Ollama AI
OLLAMA_API_URL=http://localhost:11434/api
OLLAMA_MODEL=llama3

# Email (Optional)
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password

# Sentry (Optional)
SENTRY_DSN=your-sentry-dsn

# Government APIs (Optional)
GOVERNMENT_API_TIMEOUT=30
GOVERNMENT_API_RETRY_COUNT=3
```

### Settings Files

- **Development**: `agri_advisory_app/settings/base.py`
- **Production**: `agri_advisory_app/settings/production.py`

## 📚 API Documentation

### Endpoints

#### AI Assistant
- **POST** `/api/chatbot/` - Chat with AI assistant

#### Agricultural Services
- **GET** `/api/realtime-gov/crop_recommendations/` - Get crop recommendations
- **GET** `/api/realtime-gov/government_schemes/` - Get government schemes
- **GET** `/api/realtime-gov/weather/` - Get weather data
- **GET** `/api/realtime-gov/market_prices/` - Get market prices
- **POST** `/api/realtime-gov/pest_detection/` - Pest detection

#### Location Services
- **GET** `/api/locations/search/` - Search locations
- **GET** `/api/locations/reverse/` - Reverse geocoding

#### Crop Search
- **GET** `/api/realtime-gov/crop_search/` - Search crop information

### Example API Usage

```python
import requests

# Get crop recommendations for Raebareli
response = requests.get(
    'http://localhost:8000/api/realtime-gov/crop_recommendations/',
    params={
        'location': 'Raebareli',
        'latitude': 26.2,
        'longitude': 81.2
    }
)
print(response.json())

# Chat with AI assistant
response = requests.post(
    'http://localhost:8000/api/chatbot/',
    json={
        'query': 'What crops should I grow in Raebareli?',
        'session_id': 'user123'
    }
)
print(response.json())
```

## 🧪 Testing

### Run Tests
```bash
# Run all tests
python manage.py test

# Run specific test
python manage.py test agri_advisory_app.tests.test_ai_assistant

# Run with coverage
coverage run --source='.' manage.py test
coverage report
coverage html
```

### Test Scripts
```bash
# Test AI assistant
python test_ai_simple_responses.py

# Test all services
python verify_site_simple.py

# Deep verification
python deep_verification_simple.py
```

## 📊 Monitoring

### Health Check
- **Endpoint**: `/health/`
- **Response**: JSON with system status

### Metrics
- **Endpoint**: `/metrics/`
- **Format**: Prometheus metrics

### Logs
- **Location**: `logs/django.log`
- **Level**: INFO (production), DEBUG (development)

## 🔒 Security

### Features
- **HTTPS**: SSL/TLS encryption
- **CORS**: Cross-origin resource sharing
- **Rate Limiting**: API rate limiting
- **Security Headers**: XSS, CSRF protection
- **Input Validation**: Data sanitization
- **Authentication**: JWT tokens

### Best Practices
- Use strong SECRET_KEY
- Enable DEBUG=False in production
- Use HTTPS in production
- Regular security updates
- Monitor logs for suspicious activity

## 🤝 Contributing

1. **Fork the repository**
2. **Create a feature branch**
   ```bash
   git checkout -b feature/amazing-feature
   ```
3. **Commit your changes**
   ```bash
   git commit -m 'Add amazing feature'
   ```
4. **Push to the branch**
   ```bash
   git push origin feature/amazing-feature
   ```
5. **Open a Pull Request**

### Development Setup

1. **Install development dependencies**
   ```bash
   pip install -r requirements-dev.txt
   ```

2. **Run pre-commit hooks**
   ```bash
   pre-commit install
   ```

3. **Run linting**
   ```bash
   flake8
   black .
   isort .
   ```

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **Indian Government**: For providing open agricultural APIs
- **Ollama**: For open-source AI models
- **Django**: For the excellent web framework
- **Bootstrap**: For the responsive UI components
- **Chart.js**: For data visualization

## 📞 Support

- **Issues**: [GitHub Issues](https://github.com/yourusername/krishimitra-ai/issues)
- **Discussions**: [GitHub Discussions](https://github.com/yourusername/krishimitra-ai/discussions)
- **Email**: support@krishimitra-ai.com

## 🔮 Roadmap

### Upcoming Features
- [ ] Mobile app (React Native)
- [ ] Voice commands
- [ ] IoT sensor integration
- [ ] Blockchain for supply chain
- [ ] Machine learning models
- [ ] Multi-language support
- [ ] Offline mode
- [ ] Push notifications

### Version History
- **v1.0.0**: Initial release with basic features
- **v1.1.0**: Added AI assistant and government APIs
- **v1.2.0**: Enhanced UI and location services
- **v1.3.0**: Added pest detection and market prices
- **v1.4.0**: ChatGPT-like AI responses and context awareness

---

**Made with ❤️ for Indian Farmers**

*Krishimitra AI - Empowering Agriculture with Intelligence*