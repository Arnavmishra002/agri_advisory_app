import re

def find_apis():
    print("🔍 Searching for API endpoints in JS file...")
    try:
        with open('agmarknet_main.js', 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
            
        # Regex for URLs
        urls = re.findall(r'https?://[^\s"\']+', content)
        print(f"\nFound {len(urls)} absolute URLs:")
        for url in urls[:10]:
            print(f"  - {url}")
            
        # Regex for relative API paths
        api_paths = re.findall(r'["\'](/api/[^"\']+)["\']', content)
        print(f"\nFound {len(api_paths)} relative API paths:")
        for path in set(api_paths):
            print(f"  - {path}")
            
        # Regex for .aspx paths
        aspx_paths = re.findall(r'["\']([^"\']+\.aspx)["\']', content)
        print(f"\nFound {len(aspx_paths)} .aspx paths:")
        for path in set(aspx_paths):
            print(f"  - {path}")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    find_apis()
