# 🚀 Free Hosting Deployment Guide

## Deploy to Render.com (FREE)

### Step 1: Prepare Your Repository
1. Make sure all your code is committed to GitHub
2. Your repository should be public for free hosting

### Step 2: Deploy to Render
1. Go to [render.com](https://render.com)
2. Sign up with your GitHub account
3. Click "New +" → "Web Service"
4. Connect your GitHub repository
5. Use these settings:

**Build Settings:**
- **Build Command:** `pip install -r requirements-production.txt`
- **Start Command:** `gunicorn core.wsgi:application --bind 0.0.0.0:$PORT`

**Environment Variables:**
- `DEBUG` = `False`
- `SECRET_KEY` = `your-secret-key-here` (generate a new one)
- `ALLOWED_HOSTS` = `your-app-name.onrender.com`

### Step 3: Database Setup
For free tier, you can use SQLite (already configured) or:
1. Add PostgreSQL addon in Render
2. Update DATABASE_URL environment variable

### Step 4: Static Files
Static files are handled by WhiteNoise (already configured)

## Alternative: Railway.app (FREE)

### Step 1: Deploy to Railway
1. Go to [railway.app](https://railway.app)
2. Sign up with GitHub
3. Click "New Project" → "Deploy from GitHub repo"
4. Select your repository

### Step 2: Configure
Railway will auto-detect Django and use the Procfile

## Alternative: Heroku (FREE tier discontinued, but paid)

### Step 1: Install Heroku CLI
```bash
# Download from https://devcenter.heroku.com/articles/heroku-cli
```

### Step 2: Deploy
```bash
heroku create your-app-name
git push heroku main
heroku open
```

## 🎯 Recommended: Render.com

**Why Render?**
- ✅ Free tier available
- ✅ Easy GitHub integration
- ✅ Automatic deployments
- ✅ Built-in PostgreSQL
- ✅ Custom domains
- ✅ SSL certificates

**Free Tier Limits:**
- 750 hours/month (enough for 24/7)
- Sleeps after 15 minutes of inactivity
- Takes 30 seconds to wake up

## 🔧 Post-Deployment

1. **Update ALLOWED_HOSTS** in settings.py with your actual domain
2. **Set up environment variables** for production
3. **Test all features** on the live site
4. **Set up custom domain** (optional)

## 📱 Access Your App

Once deployed, you'll get a URL like:
- `https://your-app-name.onrender.com`
- `https://your-app-name.up.railway.app`

You can access this from anywhere without running locally!