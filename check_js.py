import os

def check_file():
    print("🔍 Checking JS file...")
    try:
        size = os.path.getsize('agmarknet_main.js')
        print(f"File size: {size} bytes")
        
        with open('agmarknet_main.js', 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
            
        print(f"Content length: {len(content)}")
        
        if '.aspx' in content:
            print("✅ Found '.aspx' in content!")
            index = content.find('.aspx')
            print(f"Context: ...{content[max(0, index-50):min(len(content), index+50)]}...")
        else:
            print("❌ '.aspx' NOT found in content")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_file()
