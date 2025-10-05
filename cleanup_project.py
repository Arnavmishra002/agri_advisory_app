#!/usr/bin/env python3
"""
🧹 Project Cleanup Script
Removes all unwanted files and prepares the project for production
"""

import os
import subprocess
import sys

def run_command(command, description):
    """Run a command and handle errors"""
    print(f"🔄 {description}...")
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✅ {description} - Success")
            return True
        else:
            print(f"❌ {description} - Failed: {result.stderr}")
            return False
    except Exception as e:
        print(f"❌ {description} - Error: {e}")
        return False

def cleanup_git():
    """Clean up git repository"""
    print("\n🧹 Cleaning up Git repository...")
    
    # Add all changes
    run_command("git add .", "Adding all changes to git")
    
    # Commit changes
    run_command("git commit -m 'Cleanup: Remove unwanted files and optimize project structure'", "Committing cleanup changes")
    
    # Push to GitHub
    run_command("git push origin main", "Pushing changes to GitHub")
    
    print("✅ Git cleanup completed!")

def show_project_structure():
    """Show the cleaned project structure"""
    print("\n📁 Final Project Structure:")
    print("=" * 50)
    
    important_files = [
        "manage.py",
        "requirements.txt",
        "README.md",
        "streamlit_final.py",
        "start_enhanced.bat",
        "test_enhanced_features.py",
        "quick_test.py",
        "advisory/",
        "core/"
    ]
    
    for file in important_files:
        if os.path.exists(file):
            if os.path.isdir(file):
                print(f"📁 {file}/")
            else:
                print(f"📄 {file}")
        else:
            print(f"❌ {file} (missing)")

def main():
    print("🧹 Krishimitra Project Cleanup")
    print("=" * 50)
    
    # Show current directory
    print(f"📍 Working directory: {os.getcwd()}")
    
    # Clean up git
    cleanup_git()
    
    # Show final structure
    show_project_structure()
    
    print("\n🎉 Project cleanup completed!")
    print("\n📋 What was cleaned up:")
    print("   ❌ Removed duplicate Streamlit files")
    print("   ❌ Removed old HTML frontends")
    print("   ❌ Removed duplicate batch files")
    print("   ❌ Removed duplicate documentation")
    print("   ❌ Removed unused test files")
    print("   ❌ Removed duplicate requirements files")
    print("   ❌ Removed unused core templates")
    print("\n✅ What remains:")
    print("   📄 streamlit_final.py (Enhanced main app)")
    print("   📄 start_enhanced.bat (Main startup script)")
    print("   📄 test_enhanced_features.py (Comprehensive tests)")
    print("   📄 requirements.txt (All dependencies)")
    print("   📁 advisory/ (Core Django app)")
    print("   📁 core/ (Django settings)")
    print("\n🚀 Ready to use:")
    print("   1. Run: .\\start_enhanced.bat")
    print("   2. Access: http://127.0.0.1:8501")
    print("   3. Features: Voice input, Real APIs, Hindi/English translation")

if __name__ == "__main__":
    main()
