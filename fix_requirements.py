#!/usr/bin/env python3
"""
Fix Requirements File
Remove invalid threading dependency and redeploy
"""

import subprocess
import os

def fix_requirements_and_deploy():
    """Fix the requirements file and redeploy"""
    print("🔧 FIXING REQUIREMENTS FILE")
    print("=" * 50)
    
    try:
        # Change to project directory
        os.chdir(r"C:\AI\agri_advisory_app")
        
        # Add the fix
        print("📝 Adding requirements fix to git...")
        subprocess.run(["git", "add", "requirements-production.txt"], check=True)
        
        # Commit the fix
        print("💾 Committing requirements fix...")
        commit_message = "🔧 Fix requirements-production.txt - Remove invalid threading dependency"
        subprocess.run(["git", "commit", "-m", commit_message], check=True)
        
        # Push to GitHub (triggers Render deployment)
        print("🌐 Pushing fix to GitHub (triggers Render deployment)...")
        subprocess.run(["git", "push", "origin", "main"], check=True)
        
        print("\n✅ REQUIREMENTS FIXED AND DEPLOYED!")
        print("🔗 Your app will be updated at: https://krishmitra-zrk4.onrender.com")
        print("📊 Render Dashboard: https://dashboard.render.com/web/srv-d3ijghjipnbc73e8boi0")
        
        print("\n🔧 FIX APPLIED:")
        print("• Removed invalid 'threading>=1.0.0' dependency")
        print("• Threading is a built-in Python module")
        print("• Deployment should now succeed")
        
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Deployment error: {e}")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def main():
    """Main function"""
    success = fix_requirements_and_deploy()
    
    if success:
        print("\n🎉 REQUIREMENTS FIX COMPLETE!")
        print("The deployment should now succeed without the threading dependency error.")
        print("\n⏱️  Deployment will take a few minutes...")
        print("Check the Render dashboard for progress.")
    else:
        print("\n❌ FIX FAILED")
        print("Please check the error messages above.")

if __name__ == "__main__":
    main()



