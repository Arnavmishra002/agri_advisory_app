#!/usr/bin/env python3
"""
Cleanup and Update Script
Removes test files and updates GitHub repository
"""

import os
import subprocess
import glob
from pathlib import Path

def cleanup_test_files():
    """Remove all test files from the project"""
    print("🧹 Cleaning up test files...")
    
    # Test file patterns to remove
    test_patterns = [
        "ai_data_source_report_*.json",
        "ai_intelligence_test_results_*.json", 
        "comprehensive_test_results_*.json",
        "*_test.py",
        "*_test_*.py",
        "test_*.py",
        "test_*.html",
        "quick_*.py",
        "dynamic_*.py",
        "individual_*.py",
        "production_*.py",
        "super_*.py",
        "ultimate_*.py",
        "verify_*.py",
        "fix_*.py",
        "*_report.py",
        "*_summary.py",
        "tatus",  # Typo file
        "Working - 100- Success Rate",  # Temp file
        "start_*.bat"
    ]
    
    removed_files = []
    
    for pattern in test_patterns:
        files = glob.glob(pattern)
        for file in files:
            try:
                if os.path.exists(file):
                    os.remove(file)
                    removed_files.append(file)
                    print(f"   ✅ Removed: {file}")
            except Exception as e:
                print(f"   ❌ Error removing {file}: {e}")
    
    print(f"\n📊 Cleanup Summary:")
    print(f"   Files removed: {len(removed_files)}")
    
    return removed_files

def update_git():
    """Update Git repository"""
    print("\n🔄 Updating Git repository...")
    
    try:
        # Add all changes
        subprocess.run(["git", "add", "."], check=True)
        print("   ✅ Added all changes to git")
        
        # Commit changes
        commit_message = "🧹 Clean up test files and improve AI assistant"
        subprocess.run(["git", "commit", "-m", commit_message], check=True)
        print("   ✅ Committed changes")
        
        # Push to GitHub
        subprocess.run(["git", "push", "origin", "main"], check=True)
        print("   ✅ Pushed to GitHub")
        
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"   ❌ Git error: {e}")
        return False
    except FileNotFoundError:
        print("   ❌ Git not found. Please install Git and configure it.")
        return False

def main():
    """Main function"""
    print("🚀 CLEANUP AND UPDATE SCRIPT")
    print("=" * 50)
    
    # Change to project directory
    os.chdir(r"C:\AI\agri_advisory_app")
    print(f"📁 Working in: {os.getcwd()}")
    
    # Cleanup test files
    removed_files = cleanup_test_files()
    
    # Update Git repository
    git_success = update_git()
    
    print("\n🎉 CLEANUP COMPLETE!")
    print("=" * 50)
    print(f"📊 Files removed: {len(removed_files)}")
    print(f"🔄 Git update: {'✅ Success' if git_success else '❌ Failed'}")
    
    if git_success:
        print("\n🌐 Your GitHub repository has been updated!")
        print("   Repository: https://github.com/Arnavmishra002/agri_advisory_app")
    
    print("\n✨ Next steps:")
    print("   1. Train and improve AI assistant")
    print("   2. Run comprehensive testing")
    print("   3. Deploy to production")

if __name__ == "__main__":
    main()
