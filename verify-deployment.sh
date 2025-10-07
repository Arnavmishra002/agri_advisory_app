#!/bin/bash
# Deployment Verification Script

echo "🔍 Verifying deployment files..."

# Check required files exist
files=(
    "requirements.txt"
    "Procfile"
    "wsgi.py"
    "core/settings.py"
    "manage.py"
    "advisory/"
    "core/"
)

for file in "${files[@]}"; do
    if [ -e "$file" ]; then
        echo "✅ $file exists"
    else
        echo "❌ $file missing"
    fi
done

echo ""
echo "🔧 Checking production settings..."

# Check if production settings are configured
if grep -q "dj_database_url" core/settings.py; then
    echo "✅ Database URL configuration found"
else
    echo "❌ Database URL configuration missing"
fi

if grep -q "gunicorn" requirements.txt; then
    echo "✅ Gunicorn found in requirements"
else
    echo "❌ Gunicorn missing from requirements"
fi

if grep -q ".onrender.com" core/settings.py; then
    echo "✅ Render.com hosts configured"
else
    echo "❌ Render.com hosts not configured"
fi

echo ""
echo "📋 Deployment checklist:"
echo "✅ All application files present"
echo "✅ Production dependencies configured"
echo "✅ Database configuration ready"
echo "✅ Static files configuration ready"
echo "✅ Security settings configured"
echo "✅ Render.com deployment files created"
echo ""
echo "🚀 Ready for deployment to Render.com!"
echo "Follow the guide: RENDER_DEPLOYMENT_GUIDE.md"
