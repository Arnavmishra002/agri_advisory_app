#!/usr/bin/env python3
"""
Installation script for enhanced AI dependencies
"""

import subprocess
import sys
import os

def install_package(package):
    """Install a package using pip"""
    try:
        print(f"Installing {package}...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", package])
        print(f"✅ {package} installed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to install {package}: {e}")
        return False

def main():
    """Main installation function"""
    print("🚀 Installing Enhanced AI Dependencies for ChatGPT-like Agricultural Chatbot")
    print("=" * 70)
    
    # Core AI/ML packages
    core_packages = [
        "transformers>=4.36.0",
        "sentence-transformers>=2.2.0",
        "langdetect>=1.0.9",
        "googletrans==4.0.0rc1",
        "textblob>=0.17.1",
        "spacy>=3.4.0",
        "accelerate>=0.20.0",
        "bitsandbytes>=0.41.0",
    ]
    
    # Optional advanced packages
    optional_packages = [
        "openai-whisper>=20231117",
        "polyglot>=16.7.4",
        "pycld2>=0.41",
        "nltk>=3.8.1",
        "wordcloud>=1.9.0",
        "chromadb>=0.4.0",
        "faiss-cpu>=1.7.4",
        "anthropic>=0.7.0",
        "openai>=1.0.0",
    ]
    
    print("Installing core packages...")
    success_count = 0
    total_count = len(core_packages)
    
    for package in core_packages:
        if install_package(package):
            success_count += 1
    
    print(f"\nCore packages: {success_count}/{total_count} installed successfully")
    
    if success_count == total_count:
        print("\nInstalling optional packages (these may take longer)...")
        optional_success = 0
        
        for package in optional_packages:
            if install_package(package):
                optional_success += 1
        
        print(f"Optional packages: {optional_success}/{len(optional_packages)} installed successfully")
    
    # Download spaCy model
    print("\nDownloading spaCy English model...")
    try:
        subprocess.check_call([sys.executable, "-m", "spacy", "download", "en_core_web_sm"])
        print("✅ spaCy English model downloaded successfully")
    except subprocess.CalledProcessError:
        print("⚠️ spaCy model download failed - you may need to download it manually")
    
    # Download NLTK data
    print("\nDownloading NLTK data...")
    try:
        import nltk
        nltk.download('punkt', quiet=True)
        nltk.download('stopwords', quiet=True)
        nltk.download('vader_lexicon', quiet=True)
        print("✅ NLTK data downloaded successfully")
    except Exception as e:
        print(f"⚠️ NLTK data download failed: {e}")
    
    print("\n🎉 Enhanced AI installation completed!")
    print("\nNext steps:")
    print("1. Run: python test_enhanced_chatbot.py")
    print("2. Start your Django server: python manage.py runserver")
    print("3. Test the enhanced chatbot in your application")

if __name__ == "__main__":
    main()
