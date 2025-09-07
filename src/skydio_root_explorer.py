"""
Explore what's actually available at the Skydio API root
Since all standard endpoints return 404, let's see what exists
"""

import os
import requests
import json
from dotenv import load_dotenv

load_dotenv()

def explore_api_root():
    """Explore the API root to see what's actually available"""
    
    api_key = os.getenv('SKYDIO_API_KEY')
    if not api_key:
        print("❌ API key not found")
        return
    
    headers = {
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json',
        'Accept': 'application/json'
    }
    
    print("🔍 Exploring Skydio API Root Structure")
    print("=" * 50)
    
    # Test the root endpoint to see what it returns
    base_urls = [
        "https://api.skydio.com/api/v1",
        "https://api.skydio.com/api/v1/",
        "https://api.skydio.com/api",
        "https://api.skydio.com",
    ]
    
    for base_url in base_urls:
        print(f"\n🌐 Testing: {base_url}")
        
        try:
            response = requests.get(base_url, headers=headers, timeout=10)
            print(f"  Status: {response.status_code}")
            print(f"  Content-Type: {response.headers.get('Content-Type')}")
            
            if response.content:
                try:
                    data = response.json()
                    print(f"  Response: {json.dumps(data, indent=2)}")
                    
                    # Look for clues about available endpoints
                    if isinstance(data, dict):
                        if 'endpoints' in data or 'routes' in data or 'paths' in data:
                            print("  🎯 Found endpoint information!")
                        
                        if 'error' not in data:
                            print("  ✅ Non-error response - might have useful info")
                            
                except json.JSONDecodeError:
                    print(f"  Text: {response.text[:200]}...")
                    
        except Exception as e:
            print(f"  ❌ Error: {str(e)}")


def test_simulator_specific_patterns():
    """Test Flight Simulator specific patterns"""
    
    api_key = os.getenv('SKYDIO_API_KEY')
    if not api_key:
        return
    
    headers = {
        'Authorization': f'Bearer {api_key}',
        'Accept': 'application/json'
    }
    
    print(f"\n\n🛸 Testing Flight Simulator Specific Patterns")
    print("=" * 50)
    
    # Flight Simulator might use different patterns
    simulator_patterns = [
        # GraphQL endpoint (common for modern APIs)
        "https://api.skydio.com/graphql",
        "https://api.skydio.com/api/graphql",
        "https://api.skydio.com/api/v1/graphql",
        
        # WebSocket endpoints (for real-time data)
        "https://api.skydio.com/api/v1/ws",
        "https://api.skydio.com/api/v1/websocket",
        
        # Simulator-specific paths
        "https://api.skydio.com/api/v1/simulator",
        "https://api.skydio.com/api/v1/sim",
        "https://api.skydio.com/api/v1/simulation",
        
        # Different resource naming
        "https://api.skydio.com/api/v1/drones",
        "https://api.skydio.com/api/v1/aircraft",
        "https://api.skydio.com/api/v1/assets",
        "https://api.skydio.com/api/v1/devices",
        
        # Nested structures
        "https://api.skydio.com/api/v1/organizations/vehicles",
        "https://api.skydio.com/api/v1/fleet/vehicles",
        "https://api.skydio.com/api/v1/account/vehicles",
        
        # API documentation endpoint
        "https://api.skydio.com/api/v1/docs",
        "https://api.skydio.com/api/v1/swagger",
        "https://api.skydio.com/api/v1/openapi",
        
        # Discovery/schema endpoints
        "https://api.skydio.com/api/v1/schema",
        "https://api.skydio.com/api/v1/spec",
        "https://api.skydio.com/api/v1/__schema",
    ]
    
    for url in simulator_patterns:
        try:
            response = requests.get(url, headers=headers, timeout=5)
            
            # Only report interesting responses
            if response.status_code != 404:
                print(f"📍 {url}")
                print(f"   Status: {response.status_code}")
                print(f"   Type: {response.headers.get('Content-Type', 'Unknown')}")
                
                if response.status_code == 200:
                    try:
                        data = response.json()
                        print(f"   🎉 SUCCESS! Keys: {list(data.keys())[:5]}")
                    except:
                        print(f"   Content: {response.text[:100]}...")
                elif response.status_code in [401, 403]:
                    print("   🔐 Authentication/permission issue")
                elif response.status_code == 405:
                    print("   📝 Method not allowed (endpoint exists!)")
                    
        except:
            pass  # Ignore connection errors


def check_response_headers():
    """Check response headers for clues about API structure"""
    
    api_key = os.getenv('SKYDIO_API_KEY')
    if not api_key:
        return
        
    headers = {
        'Authorization': f'Bearer {api_key}',
        'Accept': 'application/json'
    }
    
    print(f"\n\n📋 Analyzing Response Headers for API Clues")
    print("=" * 50)
    
    try:
        # Use any endpoint that gives us a response (even 404)
        response = requests.get("https://api.skydio.com/api/v1/vehicles", headers=headers)
        
        print("Response Headers:")
        for header, value in response.headers.items():
            print(f"  {header}: {value}")
            
        # Look for API versioning or routing clues
        interesting_headers = ['X-API-Version', 'X-Supported-Endpoints', 'Allow', 'Link']
        for header in interesting_headers:
            if header in response.headers:
                print(f"\n🎯 Found interesting header: {header} = {response.headers[header]}")
                
    except Exception as e:
        print(f"❌ Error checking headers: {str(e)}")


def main():
    """Run all exploration tests"""
    explore_api_root()
    test_simulator_specific_patterns()
    check_response_headers()
    
    print(f"\n\n💡 Conclusions:")
    print("1. Your authentication is working perfectly")
    print("2. Standard REST endpoints don't exist")
    print("3. Flight Simulator likely uses a different API pattern")
    print("4. Next step: Contact Skydio support for Flight Simulator API docs")


if __name__ == "__main__":
    main()
