# Render.com Deployment Configuration for Krishimitra AI

## Overview
This Django application will be deployed to Render.com with:
- Free PostgreSQL database
- Automatic HTTPS
- Zero-downtime deployments
- Auto-deploy from GitHub

## Deployment Steps

### 1. Create GitHub Repository
1. Go to https://github.com
2. Create new repository: "krishimitra-ai"
3. Upload all project files
4. Make sure to include all files created below

### 2. Connect to Render.com
1. Go to https://render.com
2. Sign up with GitHub account
3. Click "New +" → "Web Service"
4. Connect your GitHub repository

### 3. Configure Web Service
- **Name**: krishimitra-ai
- **Environment**: Python 3
- **Build Command**: `pip install -r requirements.txt`
- **Start Command**: `gunicorn core.wsgi:application`
- **Instance Type**: Free

### 4. Add PostgreSQL Database
1. Click "New +" → "PostgreSQL"
2. Name: krishimitra-db
3. Plan: Free
4. Copy the database URL

### 5. Environment Variables
Add these in Render dashboard:
```
SECRET_KEY=your-secret-key-here
DEBUG=False
ALLOWED_HOSTS=krishimitra-ai.onrender.com
DATABASE_URL=postgresql://... (from step 4)
```

### 6. Deploy!
Click "Deploy" and wait 5-10 minutes.

## Features Included
✅ Django application with all fixes
✅ PostgreSQL database
✅ Static file serving
✅ HTTPS certificate
✅ Automatic deployments
✅ Custom domain support

## Post-Deployment
Your app will be available at:
https://krishimitra-ai.onrender.com

## Support
- Render.com has excellent documentation
- Free tier includes 750 hours/month
- Automatic scaling
- Built-in monitoring
