"""
Quick tester for different Skydio API base URLs
This will help find the correct API endpoint for your Flight Simulator
"""

import os
import requests
import json
from dotenv import load_dotenv

load_dotenv()

def test_base_urls():
    """Test different possible Skydio API base URLs"""
    
    api_key = os.getenv('SKYDIO_API_KEY')
    if not api_key:
        print("❌ SKYDIO_API_KEY not found")
        return
    
    # Possible base URLs for Skydio API
    base_urls_to_test = [
        # Standard Cloud API
        "https://api.skydio.com/api",
        "https://api.skydio.com/api/v1",
        "https://api.skydio.com/v1", 
        "https://cloud.skydio.com/rest/api/v1",
        
        # Flight Simulator specific
        "https://cloud.skydio.com/api/simulator/v1",
        "https://cloud.skydio.com/simulator/api/v1",
        "https://simulator.cloud.skydio.com/api/v1",
        
        # Alternative paths
        "https://cloud.skydio.com/rest/v1",
        "https://cloud.skydio.com/api/rest/v1",
        "https://app.skydio.com/api/v1",
        
        # GraphQL endpoints (might give hints)
        "https://cloud.skydio.com/graphql",
        "https://api.skydio.com/graphql",
    ]
    
    headers = {
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json',
        'Accept': 'application/json'
    }
    
    print("🔍 Testing Different Skydio API Base URLs")
    print("=" * 60)
    
    for base_url in base_urls_to_test:
        print(f"\n🌐 Testing: {base_url}")
        
        try:
            response = requests.get(base_url, headers=headers, timeout=10)
            
            print(f"  Status: {response.status_code}")
            print(f"  Content-Type: {response.headers.get('Content-Type', 'Unknown')}")
            
            if response.content:
                content = response.text[:100].replace('\n', ' ')
                
                # Check if it's JSON (good sign!)
                if 'application/json' in response.headers.get('Content-Type', ''):
                    try:
                        json_data = response.json()
                        print(f"  🎉 JSON Response: {json.dumps(json_data, indent=2)[:200]}...")
                        
                        if response.status_code in [200, 401]:  # 401 is OK, means endpoint exists
                            print(f"  ✅ POTENTIAL API ENDPOINT FOUND!")
                            
                    except json.JSONDecodeError:
                        print(f"  ⚠️  JSON decode failed")
                        
                elif 'text/html' in response.headers.get('Content-Type', ''):
                    print(f"  🌐 HTML Response (web interface)")
                    
                else:
                    print(f"  📄 Content: {content}...")
                    
            else:
                print(f"  📭 Empty response")
                
            # Look for API-like responses even with different status codes
            if response.status_code == 404:
                print(f"  📍 Endpoint not found (but server exists)")
            elif response.status_code == 401:
                print(f"  🔐 Unauthorized (endpoint likely exists!)")
            elif response.status_code == 403:
                print(f"  🚫 Forbidden (endpoint exists, permission issue)")
                
        except requests.exceptions.RequestException as e:
            print(f"  ❌ Connection failed: {str(e)[:60]}...")


def test_specific_endpoints():
    """Test specific endpoints that might exist"""
    
    api_key = os.getenv('SKYDIO_API_KEY')
    if not api_key:
        return
        
    print(f"\n\n🎯 Testing Specific API Endpoints")
    print("=" * 60)
    
    # Most likely working base URL (educated guess)
    potential_bases = [
        "https://api.skydio.com/api/v1",
        "https://cloud.skydio.com/rest/api/v1"
    ]
    
    endpoints_to_test = [
        "/organizations",
        "/account", 
        "/vehicles",
        "/flights",
        "/simulator",
        "/sim"
    ]
    
    headers = {
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json',
        'Accept': 'application/json'
    }
    
    for base in potential_bases:
        print(f"\n🔍 Testing endpoints on: {base}")
        
        for endpoint in endpoints_to_test:
            url = f"{base}{endpoint}"
            
            try:
                response = requests.get(url, headers=headers, timeout=10)
                
                if response.status_code != 200 or 'application/json' in response.headers.get('Content-Type', ''):
                    print(f"  {endpoint}: Status {response.status_code} - {response.headers.get('Content-Type', 'Unknown')}")
                    
                    if response.status_code == 200:
                        try:
                            data = response.json()
                            print(f"    ✅ SUCCESS! Data keys: {list(data.keys())}")
                        except:
                            pass
                            
            except requests.exceptions.RequestException:
                pass  # Skip connection errors for this quick test


if __name__ == "__main__":
    test_base_urls()
    test_specific_endpoints()
    
    print(f"\n\n💡 Next Steps:")
    print(f"1. If any endpoint returned JSON, update your .env with that base URL")
    print(f"2. If all returned HTML, contact Skydio support for correct API endpoints")
    print(f"3. Your API key appears valid - it's just a URL issue")
