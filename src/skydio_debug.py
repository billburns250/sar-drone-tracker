"""
Debug script for Skydio API connection issues
This will help diagnose what's happening with the API calls
"""

import os
import requests
import json
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def debug_skydio_connection():
    """Debug Skydio API connection with detailed output"""
    
    print("🔍 Skydio API Debug Script")
    print("=" * 50)
    
    # Get credentials
    api_key = os.getenv('SKYDIO_API_KEY')
    base_url = os.getenv('SKYDIO_BASE_URL', 'https://cloud.skydio.com/api/v1')
    
    print(f"API Key: {'*' * (len(api_key)-4) + api_key[-4:] if api_key else 'NOT SET'}")
    print(f"Base URL: {base_url}")
    print()
    
    if not api_key:
        print("❌ SKYDIO_API_KEY not found in .env file")
        return
    
    # Test different authentication methods
    auth_methods = [
        ("Bearer token", {"Authorization": f"Bearer {api_key}"}),
        ("API Key header", {"X-API-Key": api_key}),
        ("Skydio-API-Key header", {"Skydio-API-Key": api_key}),
    ]
    
    # Test different endpoints
    endpoints_to_try = [
        "/user/profile",
        "/user",
        "/account",
        "/vehicles",
        "/fleet",
        "/organizations",
        "/health",
        "/status",
        ""  # Root endpoint
    ]
    
    for auth_name, headers in auth_methods:
        print(f"🔑 Testing {auth_name}...")
        headers.update({
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        })
        
        for endpoint in endpoints_to_try:
            url = f"{base_url.rstrip('/')}/{endpoint.lstrip('/')}" if endpoint else base_url
            
            try:
                print(f"  GET {url}")
                response = requests.get(url, headers=headers, timeout=10)
                
                print(f"    Status: {response.status_code}")
                print(f"    Headers: {dict(response.headers)}")
                
                # Try to get response content
                if response.content:
                    try:
                        json_data = response.json()
                        print(f"    JSON Response: {json.dumps(json_data, indent=2)[:200]}...")
                        
                        if response.status_code == 200:
                            print(f"    ✅ SUCCESS with {auth_name} on {endpoint}")
                            return True, auth_name, endpoint, headers
                            
                    except json.JSONDecodeError:
                        print(f"    Text Response: {response.text[:200]}...")
                        
                    if response.status_code == 401:
                        print(f"    🔑 Authentication failed")
                    elif response.status_code == 403:
                        print(f"    🚫 Forbidden (check permissions)")
                    elif response.status_code == 404:
                        print(f"    📍 Endpoint not found")
                    else:
                        print(f"    ❓ Unexpected response")
                else:
                    print(f"    📭 Empty response")
                    
            except requests.exceptions.RequestException as e:
                print(f"    ❌ Request failed: {str(e)}")
                
            print()
            
    print("❌ No successful authentication method found")
    return False, None, None, None


def test_flight_simulator_endpoints():
    """Test Flight Simulator specific endpoints"""
    print("\n🛸 Testing Flight Simulator Specific Endpoints...")
    
    api_key = os.getenv('SKYDIO_API_KEY')
    if not api_key:
        return
        
    # Flight simulator might use different endpoints
    sim_endpoints = [
        "https://cloud.skydio.com/api/v1/simulator",
        "https://cloud.skydio.com/api/v1/sim",
        "https://cloud.skydio.com/simulator/api/v1",
        "https://sim.skydio.com/api/v1",
        "https://simulator.skydio.com/api/v1",
    ]
    
    headers = {
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json',
        'Accept': 'application/json'
    }
    
    for base_url in sim_endpoints:
        try:
            print(f"Testing: {base_url}")
            response = requests.get(base_url, headers=headers, timeout=10)
            print(f"  Status: {response.status_code}")
            
            if response.status_code not in [404, 502, 503]:
                print(f"  Response: {response.text[:100]}...")
                if response.status_code == 200:
                    print(f"  ✅ Possible Flight Simulator endpoint!")
                    
        except requests.exceptions.RequestException as e:
            print(f"  Connection failed: {str(e)}")


def check_env_file():
    """Check .env file configuration"""
    print("\n📄 Checking .env file...")
    
    if not os.path.exists('.env'):
        print("❌ .env file not found in current directory")
        print(f"Current directory: {os.getcwd()}")
        return
        
    with open('.env', 'r') as f:
        lines = f.readlines()
        
    print(f"✅ .env file found with {len(lines)} lines")
    
    required_vars = ['SKYDIO_API_KEY', 'SKYDIO_BASE_URL']
    for var in required_vars:
        value = os.getenv(var)
        if value:
            if var == 'SKYDIO_API_KEY':
                print(f"  {var}: {'*' * (len(value)-4) + value[-4:]}")
            else:
                print(f"  {var}: {value}")
        else:
            print(f"  {var}: ❌ NOT SET")


def main():
    check_env_file()
    
    success, auth_method, endpoint, headers = debug_skydio_connection()
    
    if success:
        print(f"\n🎉 Found working configuration:")
        print(f"  Authentication: {auth_method}")
        print(f"  Endpoint: {endpoint}")
        print(f"  Headers: {headers}")
        
        print(f"\n💡 Update your skydio_client.py to use:")
        print(f"  - Endpoint: {endpoint}")
        print(f"  - Headers: {headers}")
    else:
        test_flight_simulator_endpoints()
        
        print(f"\n🔧 Troubleshooting suggestions:")
        print(f"1. Verify your API key is correct")
        print(f"2. Check if you need different authentication for Flight Simulator")
        print(f"3. Confirm your Skydio account has API access enabled")
        print(f"4. Try different base URLs (simulator vs production)")
        print(f"5. Contact Skydio support for correct Flight Simulator API endpoints")


if __name__ == "__main__":
    main()
