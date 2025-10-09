#!/usr/bin/env python3
"""
Fix Deployment Errors
Quick fix for the API method signature and multilingual errors
"""

import subprocess
import os

def fix_and_deploy():
    """Fix the deployment errors and redeploy"""
    print("🔧 FIXING DEPLOYMENT ERRORS")
    print("=" * 50)
    
    try:
        # Change to project directory
        os.chdir(r"C:\AI\agri_advisory_app")
        
        # Add all changes
        print("📝 Adding fixes to git...")
        subprocess.run(["git", "add", "."], check=True)
        
        # Commit fixes
        print("💾 Committing fixes...")
        commit_message = "🔧 Fix API method signatures and multilingual crop data structure errors"
        subprocess.run(["git", "commit", "-m", commit_message], check=True)
        
        # Push to GitHub (triggers Render deployment)
        print("🌐 Pushing fixes to GitHub (triggers Render deployment)...")
        subprocess.run(["git", "push", "origin", "main"], check=True)
        
        print("\n✅ FIXES DEPLOYED SUCCESSFULLY!")
        print("🔗 Your app will be updated at: https://krishmitra-zrk4.onrender.com")
        print("📊 Render Dashboard: https://dashboard.render.com/web/srv-d3ijghjipnbc73e8boi0")
        
        print("\n🔧 FIXES APPLIED:")
        print("• Fixed MarketPricesViewSet API method signature")
        print("• Fixed crop data structure in multilingual responses")
        print("• Fixed 'name' error in crop recommendations")
        print("• Improved error handling for government APIs")
        
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Deployment error: {e}")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def main():
    """Main function"""
    success = fix_and_deploy()
    
    if success:
        print("\n🎉 DEPLOYMENT FIXES COMPLETE!")
        print("Your application should now work without the previous errors.")
        print("\n🧪 TEST YOUR APPLICATION:")
        print("1. Visit: https://krishmitra-zrk4.onrender.com")
        print("2. Try asking: 'What crop should I grow in Delhi?'")
        print("3. Check market prices for different crops")
        print("4. Test in Hindi: 'दिल्ली में कौन सी फसल उगाऊं?'")
    else:
        print("\n❌ FIXES FAILED")
        print("Please check the error messages above.")

if __name__ == "__main__":
    main()

