#!/bin/bash

# Quick Deployment Script for Agricultural Advisory App
echo "🚀 Preparing for deployment..."

# Clear Render build cache
echo "🧹 Clearing build cache..."
rm -rf .render-build-cache-bust
echo "Build timestamp: $(date +%s)" > .render-build-cache-bust

# Check if we're in the right directory
if [ ! -f "backend/manage.py" ] && [ ! -f "manage.py" ]; then
    echo "❌ Error: Please run this script from the agri_advisory_app repository root"
    exit 1
fi

# Check if git is initialized
if [ ! -d ".git" ]; then
    echo "📦 Initializing git repository..."
    git init
    git add .
    git commit -m "Initial commit for deployment"
fi

# Check if requirements-production.txt exists
if [ ! -f "backend/requirements-production.txt" ]; then
    echo "❌ Error: requirements-production.txt not found"
    exit 1
fi

# Check if Procfile exists
if [ ! -f "Procfile" ]; then
    echo "❌ Error: Procfile not found"
    exit 1
fi

echo "✅ All deployment files are ready!"
echo ""
echo "📋 Next steps:"
echo "1. Push your code to GitHub:"
echo "   git remote add origin https://github.com/yourusername/your-repo.git"
echo "   git push -u origin main"
echo ""
echo "2. Go to https://render.com and deploy:"
echo "   - Connect your GitHub repository"
echo "   - Use rootDir: backend"
echo "   - Use Build Command: pip install -r requirements-production.txt && python manage.py collectstatic --noinput  (from backend/)"
echo "   - Use Start Command: gunicorn core.wsgi:application --bind 0.0.0.0:\$PORT"
echo "   - Set DEBUG=False"
echo ""
echo "3. Your app will be available at: https://your-app-name.onrender.com"
echo ""
echo "🎉 Happy farming with your online agricultural advisory app!"

echo ""
echo "3. Your app will be available at: https://your-app-name.onrender.com"
echo ""
echo "🎉 Happy farming with your online agricultural advisory app!"
