import re

def search_context():
    print("🔍 Searching for keywords in JS file...")
    try:
        with open('agmarknet_main.js', 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
            
        keywords = ['/api', 'price', 'fetch', 'axios', 'http', 'agmarknet.gov.in']
        
        for kw in keywords:
            print(f"\n--- Searching for '{kw}' ---")
            matches = [m.start() for m in re.finditer(re.escape(kw), content, re.IGNORECASE)]
            print(f"Found {len(matches)} occurrences")
            
            for i, pos in enumerate(matches[:5]): # Show first 5 contexts
                start = max(0, pos - 50)
                end = min(len(content), pos + 100)
                print(f"  Context {i+1}: ...{content[start:end]}...")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    search_context()
