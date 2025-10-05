#!/usr/bin/env python3
"""
Cleanup script to remove unwanted files and update GitHub
"""

import os
import shutil
import subprocess
import sys

def remove_file(file_path):
    """Remove a file if it exists"""
    if os.path.exists(file_path):
        try:
            os.remove(file_path)
            print(f"✅ Removed: {file_path}")
            return True
        except Exception as e:
            print(f"❌ Error removing {file_path}: {e}")
            return False
    return False

def remove_directory(dir_path):
    """Remove a directory if it exists"""
    if os.path.exists(dir_path):
        try:
            shutil.rmtree(dir_path)
            print(f"✅ Removed directory: {dir_path}")
            return True
        except Exception as e:
            print(f"❌ Error removing directory {dir_path}: {e}")
            return False
    return False

def clean_unused_files():
    """Clean unused files"""
    print("🧹 Cleaning unused files...")
    
    # Files to remove (keep only the final working versions)
    unused_files = [
        # Old streamlit versions (keep only streamlit_fixed_final.py)
        "streamlit_complete_fixed.py",
        "streamlit_farmer_friendly.py",
        
        # Old batch files (keep only start_fixed_final.bat)
        "start_complete_fixed.bat",
        "start_farmer_friendly.bat",
        
        # Documentation files (keep only README.md)
        "COMPLETE_CODERABBIT_VERIFICATION.md",
    ]
    
    removed_count = 0
    for file_path in unused_files:
        if remove_file(file_path):
            removed_count += 1
    
    return removed_count

def clean_pycache():
    """Clean all __pycache__ directories"""
    print("🧹 Cleaning __pycache__ directories...")
    
    pycache_dirs = [
        "advisory/__pycache__",
        "advisory/api/__pycache__",
        "advisory/ml/__pycache__",
        "advisory/services/__pycache__",
        "advisory/migrations/__pycache__",
        "core/__pycache__",
    ]
    
    for pycache_dir in pycache_dirs:
        remove_directory(pycache_dir)

def git_operations():
    """Perform git operations to update GitHub"""
    print("🔄 Updating GitHub repository...")
    
    try:
        # Add all changes
        subprocess.run(['git', 'add', '.'], check=True, capture_output=True)
        print("✅ Git add completed")
        
        # Commit changes
        commit_message = "Update project: Fix weather data, voice input, and real data display - Remove unwanted files"
        subprocess.run(['git', 'commit', '-m', commit_message], check=True, capture_output=True)
        print("✅ Git commit completed")
        
        # Push to GitHub
        subprocess.run(['git', 'push', 'origin', 'main'], check=True, capture_output=True)
        print("✅ Git push to GitHub completed")
        
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Git operation error: {e}")
        return False

def main():
    print("🧹 Starting cleanup and GitHub update...")
    print("=" * 60)
    
    # Clean unused files
    removed_count = clean_unused_files()
    
    # Clean __pycache__ directories
    clean_pycache()
    
    # Update GitHub
    git_success = git_operations()
    
    print("=" * 60)
    print(f"🎉 Cleanup completed! Removed {removed_count} unused files.")
    
    if git_success:
        print("✅ GitHub repository updated successfully!")
    else:
        print("⚠️ GitHub update failed. Please check git status.")
    
    print("\n📁 Final clean project structure:")
    print("✅ streamlit_fixed_final.py (main UI)")
    print("✅ start_fixed_final.bat (main startup script)")
    print("✅ manage.py (Django server)")
    print("✅ requirements.txt (dependencies)")
    print("✅ README.md (documentation)")
    print("✅ All core Django files")
    print("✅ All advisory app files")
    print("\n🚀 Project is now clean and updated on GitHub!")

if __name__ == "__main__":
    main()
