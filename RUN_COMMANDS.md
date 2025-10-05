# 🚀 Commands to Run Your Enhanced Agricultural Chatbot

## 📋 **Quick Start Commands**

### **1. Setup Environment**
```bash
# Navigate to project directory
cd C:\AI\agri_advisory_app

# Create virtual environment (if not exists)
python -m venv venv

# Activate virtual environment
# On Windows:
.\venv\Scripts\Activate.ps1
# Or:
.\venv\Scripts\activate.bat

# On Linux/Mac:
source venv/bin/activate
```

### **2. Install Dependencies**
```bash
# Install basic dependencies first
pip install -r requirements_basic.txt

# Install enhanced AI dependencies (optional)
pip install -r requirements.txt
```

### **3. Database Setup**
```bash
# Create database migrations for new chat models
python manage.py makemigrations advisory

# Apply migrations
python manage.py migrate

# Create superuser (optional)
python manage.py createsuperuser
```

### **4. Run the Application**

#### **Option A: Development Server**
```bash
# Run Django development server
python manage.py runserver

# Access the application:
# - Backend API: http://localhost:8000/api/
# - Admin Panel: http://localhost:8000/admin/
# - API Docs: http://localhost:8000/api/schema/swagger-ui/
```

#### **Option B: Docker (Recommended)**
```bash
# Build and run with Docker
docker-compose up --build

# Run in background
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

### **5. Start Background Services**
```bash
# Start Celery worker (in separate terminal)
celery -A core worker --loglevel=info

# Start Celery beat scheduler (in separate terminal)
celery -A core beat --loglevel=info
```

## 🧪 **Testing Commands**

### **Test Enhanced Chatbot**
```bash
# Run basic test
python simple_test_chatbot.py

# Run Django tests
python manage.py test

# Run specific test
python manage.py test advisory.tests

# Run with coverage
pip install coverage
coverage run --source='.' manage.py test
coverage report
coverage html
```

### **Test API Endpoints**
```bash
# Test chatbot endpoint
curl -X POST http://localhost:8000/api/advisories/chatbot/ \
  -H "Content-Type: application/json" \
  -d '{"query": "Hello! How are you?", "language": "en", "user_id": "test_user"}'

# Test multilingual endpoint
curl -X POST http://localhost:8000/api/advisories/chatbot/ \
  -H "Content-Type: application/json" \
  -d '{"query": "नमस्ते! आप कैसे हैं?", "language": "hi", "user_id": "test_user"}'

# Test weather endpoint
curl "http://localhost:8000/api/weather/current/?lat=28.6139&lon=77.2090&lang=en"

# Test market prices endpoint
curl "http://localhost:8000/api/market-prices/prices/?lat=28.6139&lon=77.2090&lang=en"
```

## 🔧 **Development Commands**

### **Database Management**
```bash
# Create new migration
python manage.py makemigrations

# Apply migrations
python manage.py migrate

# Show migration status
python manage.py showmigrations

# Reset migrations (careful!)
python manage.py migrate advisory zero
```

### **Code Quality**
```bash
# Install development tools
pip install flake8 black isort

# Format code
black advisory/
isort advisory/

# Check code quality
flake8 advisory/

# Run linting
python -m flake8 advisory/ --max-line-length=100
```

### **Performance Testing**
```bash
# Install performance tools
pip install locust

# Run performance tests
locust -f performance_tests.py --host=http://localhost:8000
```

## 🐳 **Docker Commands**

### **Docker Development**
```bash
# Build Docker image
docker build -t agri-advisory-app .

# Run container
docker run -p 8000:8000 agri-advisory-app

# Run with environment variables
docker run -p 8000:8000 -e DEBUG=True agri-advisory-app

# View container logs
docker logs <container_id>

# Execute commands in container
docker exec -it <container_id> bash
```

### **Docker Compose**
```bash
# Start all services
docker-compose up

# Start in background
docker-compose up -d

# Stop all services
docker-compose down

# Rebuild services
docker-compose up --build

# View service logs
docker-compose logs web
docker-compose logs db
docker-compose logs redis

# Scale services
docker-compose up --scale web=3
```

## 📊 **Monitoring Commands**

### **Check Application Status**
```bash
# Check if Django is running
curl http://localhost:8000/api/

# Check health endpoint
curl http://localhost:8000/api/health/

# Check database connection
python manage.py check --database default

# Check Redis connection
python manage.py shell -c "from django.core.cache import cache; print(cache.get('test'))"
```

### **View Logs**
```bash
# View Django logs
tail -f logs/django.log

# View application logs
tail -f logs/app.log

# View error logs
tail -f logs/error.log
```

## 🚀 **Production Commands**

### **Production Deployment**
```bash
# Install production dependencies
pip install gunicorn psycopg2-binary

# Run with Gunicorn
gunicorn --bind 0.0.0.0:8000 core.wsgi:application

# Run with multiple workers
gunicorn --workers 4 --bind 0.0.0.0:8000 core.wsgi:application

# Run with production settings
python manage.py runserver 0.0.0.0:8000 --settings=core.settings_production
```

### **Production Docker**
```bash
# Use production Docker Compose
docker-compose -f docker-compose.prod.yml up -d

# Run production migrations
docker-compose -f docker-compose.prod.yml exec web python manage.py migrate

# Collect static files
docker-compose -f docker-compose.prod.yml exec web python manage.py collectstatic --noinput
```

## 🔍 **Troubleshooting Commands**

### **Common Issues**
```bash
# Check Python version
python --version

# Check installed packages
pip list

# Check Django version
python manage.py --version

# Check database connection
python manage.py dbshell

# Clear cache
python manage.py shell -c "from django.core.cache import cache; cache.clear()"

# Reset database (careful!)
python manage.py flush

# Check for errors
python manage.py check
```

### **Debug Mode**
```bash
# Run in debug mode
DEBUG=True python manage.py runserver

# Run with verbose logging
python manage.py runserver --verbosity=2

# Run shell for debugging
python manage.py shell
```

## 📱 **Frontend Commands**

### **React Frontend**
```bash
# Navigate to frontend
cd frontend

# Install dependencies
npm install

# Start development server
npm start

# Build for production
npm run build

# Run tests
npm test
```

## 🎯 **Quick Test Commands**

### **Test All Features**
```bash
# Test basic functionality
python manage.py test advisory.tests.TestAdvancedChatbot

# Test API endpoints
python manage.py test advisory.tests.TestAPIEndpoints

# Test multilingual support
python manage.py test advisory.tests.TestMultilingualSupport

# Test chat persistence
python manage.py test advisory.tests.TestChatPersistence
```

## 📋 **Complete Startup Sequence**

```bash
# 1. Setup
cd C:\AI\agri_advisory_app
python -m venv venv
.\venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements_basic.txt

# 3. Database setup
python manage.py makemigrations advisory
python manage.py migrate

# 4. Run application
python manage.py runserver

# 5. Test chatbot (in another terminal)
curl -X POST http://localhost:8000/api/advisories/chatbot/ \
  -H "Content-Type: application/json" \
  -d '{"query": "Hello! Test message", "language": "en", "user_id": "test_user"}'
```

## ✅ **Verification Commands**

```bash
# Check if everything is working
python manage.py check
python manage.py test
python simple_test_chatbot.py

# Access application
# - API: http://localhost:8000/api/
# - Admin: http://localhost:8000/admin/
# - Docs: http://localhost:8000/api/schema/swagger-ui/
```

**Your enhanced agricultural chatbot is now ready to run!** 🎉
