#!/usr/bin/env python3
"""
Deployment Script for Krishimitra AI
Automates GitHub and Render deployment process
"""

import os
import subprocess
import sys
import json
from datetime import datetime

def run_command(command, description=""):
    """Run a shell command and return the result"""
    print(f"Running: {description or command}")
    try:
        result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
        print(f"Success: {description or command}")
        return result.stdout
    except subprocess.CalledProcessError as e:
        print(f"Error: {description or command}")
        print(f"Error output: {e.stderr}")
        return None

def check_git_status():
    """Check git status and show changes"""
    print("Checking Git Status...")
    
    # Check if we're in a git repository
    if not os.path.exists('.git'):
        print("Not in a git repository. Please initialize git first.")
        return False
    
    # Show git status
    run_command("git status", "Git Status")
    
    # Show staged changes
    staged = run_command("git diff --cached --name-only", "Staged Changes")
    if staged:
        print(f"Staged files:\n{staged}")
    
    # Show unstaged changes
    unstaged = run_command("git diff --name-only", "Unstaged Changes")
    if unstaged:
        print(f"Unstaged files:\n{unstaged}")
    
    return True

def commit_changes():
    """Commit all changes to git"""
    print("Committing Changes...")
    
    # Add all files
    run_command("git add .", "Adding all files")
    
    # Commit with timestamp
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    commit_message = f"Update Krishimitra AI - {timestamp}"
    
    result = run_command(f'git commit -m "{commit_message}"', "Committing changes")
    
    if result:
        print("Changes committed successfully")
        return True
    else:
        print("Failed to commit changes")
        return False

def push_to_github():
    """Push changes to GitHub"""
    print("Pushing to GitHub...")
    
    # Get current branch
    branch_result = run_command("git branch --show-current", "Getting current branch")
    if not branch_result:
        print("Could not determine current branch")
        return False
    
    current_branch = branch_result.strip()
    print(f"Current branch: {current_branch}")
    
    # Push to GitHub
    result = run_command(f"git push origin {current_branch}", f"Pushing to GitHub ({current_branch})")
    
    if result:
        print("Successfully pushed to GitHub")
        return True
    else:
        print("Failed to push to GitHub")
        return False

def create_deployment_summary():
    """Create a deployment summary"""
    print("Creating Deployment Summary...")
    
    summary = {
        "timestamp": datetime.now().isoformat(),
        "version": "1.4.0",
        "features": [
            "AI Assistant with ChatGPT-like responses",
            "Real-time government API integration",
            "Location-based services",
            "Crop recommendations",
            "Weather data",
            "Market prices",
            "Government schemes",
            "Pest detection",
            "Mobile-friendly UI",
            "Docker support",
            "Render deployment ready"
        ],
        "deployment_files": [
            "requirements.txt",
            "render.yaml",
            "Dockerfile",
            "docker-compose.yml",
            "nginx.conf",
            ".gitignore",
            "README.md",
            "production.py"
        ],
        "status": "Ready for deployment"
    }
    
    with open("deployment_summary.json", "w") as f:
        json.dump(summary, f, indent=2)
    
    print("Deployment summary created: deployment_summary.json")
    return True

def check_deployment_files():
    """Check if all deployment files exist"""
    print("Checking Deployment Files...")
    
    required_files = [
        "requirements.txt",
        "render.yaml",
        "Dockerfile",
        "docker-compose.yml",
        "nginx.conf",
        ".gitignore",
        "README.md",
        "agri_advisory_app/settings/production.py"
    ]
    
    missing_files = []
    for file_path in required_files:
        if not os.path.exists(file_path):
            missing_files.append(file_path)
        else:
            print(f"Found: {file_path}")
    
    if missing_files:
        print(f"Missing files: {missing_files}")
        return False
    else:
        print("All deployment files present")
        return True

def update_github_repository():
    """Update GitHub repository with all changes"""
    print("Updating GitHub Repository...")
    
    # Check git status
    if not check_git_status():
        return False
    
    # Check deployment files
    if not check_deployment_files():
        return False
    
    # Commit changes
    if not commit_changes():
        return False
    
    # Push to GitHub
    if not push_to_github():
        return False
    
    # Create deployment summary
    create_deployment_summary()
    
    print("GitHub repository updated successfully!")
    return True

def render_deployment_instructions():
    """Print Render deployment instructions"""
    print("\n" + "="*60)
    print("RENDER DEPLOYMENT INSTRUCTIONS")
    print("="*60)
    
    instructions = """
1. Go to https://render.com and sign up/login
2. Click "New +" and select "Web Service"
3. Connect your GitHub account
4. Select your Krishimitra AI repository
5. Configure the service:
   - Name: krishimitra-ai
   - Environment: Python 3
   - Build Command: pip install -r requirements.txt && python manage.py collectstatic --noinput
   - Start Command: gunicorn agri_advisory_app.wsgi:application
   - Python Version: 3.11

6. Set Environment Variables:
   - DJANGO_SETTINGS_MODULE=agri_advisory_app.settings.production
   - SECRET_KEY=your-secret-key-here
   - DEBUG=False
   - ALLOWED_HOSTS=your-app-name.onrender.com
   - DATABASE_URL=postgresql://user:password@host:port/database
   - REDIS_URL=redis://user:password@host:port

7. Click "Create Web Service"
8. Wait for deployment to complete
9. Your app will be available at: https://your-app-name.onrender.com

10. Set up database:
    - Go to Render dashboard
    - Create a PostgreSQL database
    - Copy the database URL to your environment variables
    - Run migrations in the Render console

11. Optional: Set up Redis for caching
    - Create a Redis instance in Render
    - Copy the Redis URL to your environment variables
"""
    
    print(instructions)
    
    print("\n" + "="*60)
    print("DEPLOYMENT CHECKLIST")
    print("="*60)
    
    checklist = """
All files updated and committed
GitHub repository updated
Requirements.txt updated
Production settings configured
Docker files created
Render configuration ready
README.md updated
.gitignore configured
Environment variables documented
Deployment instructions provided

Next Steps:
1. Deploy to Render using the instructions above
2. Set up environment variables
3. Run database migrations
4. Test the deployed application
5. Set up monitoring and logging
"""
    
    print(checklist)

def main():
    """Main deployment function"""
    print("Krishimitra AI - Deployment Script")
    print("="*50)
    
    # Update GitHub repository
    if update_github_repository():
        print("\nGitHub repository updated successfully!")
        
        # Show Render deployment instructions
        render_deployment_instructions()
        
        print("\nDeployment preparation complete!")
        print("Your Krishimitra AI system is ready for Render deployment!")
        
    else:
        print("\nDeployment preparation failed!")
        print("Please check the errors above and try again.")
        sys.exit(1)

if __name__ == "__main__":
    main()
