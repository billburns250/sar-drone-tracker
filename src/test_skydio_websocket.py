"""
Simple WebSocket test script to debug Skydio live telemetry connection
This tries multiple different methods to confirm which methods work
"""

import os
import asyncio
import websockets
import json
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

async def test_websocket_connection():
    """Test WebSocket connection to Skydio live telemetry"""
    
    api_token = os.getenv('API_TOKEN')
    drone_serial = "sim-k8x4ocd7"  # Your flying drone
    
    if not api_token:
        print("ERROR: API_TOKEN not found in environment")
        return
    
    # Test different WebSocket URLs
    websocket_urls = [
        f"wss://stream.skydio.com/data/{drone_serial}",
        f"wss://api.skydio.com/stream/{drone_serial}",
        f"wss://cloud.skydio.com/stream/{drone_serial}",
        f"wss://stream.skydio.com/telemetry/{drone_serial}",
    ]
    
    for url in websocket_urls:
        print(f"\n=== Testing URL: {url} ===")
        
        try:
            # Try different header formats
            header_formats = [
                {"Authorization": f"ApiToken {api_token}"},
                {"Authorization": f"Bearer {api_token}"},
                {},  # No auth headers
            ]
            
            for i, headers in enumerate(header_formats):
                print(f"  Attempt {i+1}: Headers = {headers}")
                
                try:
                    # Use websockets.connect without extra_headers for compatibility
                    if headers:
                        # Some versions use different parameter names
                        try:
                            async with websockets.connect(url, extra_headers=headers) as websocket:
                                print(f"    SUCCESS: Connected with extra_headers!")
                                await test_receive_messages(websocket, timeout=5)
                                break
                        except TypeError:
                            # Try different parameter name
                            async with websockets.connect(url, additional_headers=headers) as websocket:
                                print(f"    SUCCESS: Connected with additional_headers!")
                                await test_receive_messages(websocket, timeout=5)
                                break
                    else:
                        async with websockets.connect(url) as websocket:
                            print(f"    SUCCESS: Connected without auth!")
                            await test_receive_messages(websocket, timeout=5)
                            break
                            
                except Exception as e:
                    print(f"    FAILED: {e}")
                    continue
                    
        except Exception as e:
            print(f"  Connection failed: {e}")

async def test_receive_messages(websocket, timeout=5):
    """Test receiving messages from WebSocket"""
    try:
        print("    Waiting for messages...")
        
        # Wait for messages with timeout
        message = await asyncio.wait_for(websocket.recv(), timeout=timeout)
        
        print(f"    RECEIVED MESSAGE:")
        try:
            # Try to parse as JSON
            data = json.loads(message)
            print(f"      JSON: {json.dumps(data, indent=2)[:200]}...")
        except json.JSONDecodeError:
            # Not JSON, show raw
            print(f"      RAW: {message[:200]}...")
            
        # Check for GPS data
        if isinstance(data, dict):
            gps_keys = ["gps", "location", "position", "latitude", "longitude", "coordinates"]
            found_gps = any(key in str(data).lower() for key in gps_keys)
            print(f"      Contains GPS data: {found_gps}")
            
    except asyncio.TimeoutError:
        print(f"    No messages received within {timeout} seconds")
    except Exception as e:
        print(f"    Error receiving message: {e}")

async def test_alternative_approach():
    """Test alternative approaches for live telemetry"""
    
    print(f"\n=== Testing Alternative Approaches ===")
    
    # Test if there's a REST endpoint for recent telemetry
    import requests
    
    api_token = os.getenv('API_TOKEN')
    headers = {
        "Accept": "application/json",
        "Authorization": f"ApiToken {api_token}"
    }
    
    # Try various REST endpoints that might have recent telemetry
    endpoints = [
        "v0/vehicles/sim-k8x4ocd7/telemetry",
        "v0/vehicles/sim-k8x4ocd7/status", 
        "v0/flights?vehicle_serial=sim-k8x4ocd7&limit=1",
        "v1/vehicles/sim-k8x4ocd7/live_telemetry",
        "v1/telemetry/sim-k8x4ocd7",
    ]
    
    for endpoint in endpoints:
        url = f"https://api.skydio.com/api/{endpoint}"
        print(f"  Testing REST: {url}")
        
        try:
            response = requests.get(url, headers=headers, timeout=10)
            print(f"    Status: {response.status_code}")
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    print(f"    Response keys: {list(data.keys())}")
                    
                    if "data" in data:
                        inner_data = data["data"]
                        if isinstance(inner_data, dict):
                            print(f"    Data keys: {list(inner_data.keys())}")
                        elif isinstance(inner_data, list) and inner_data:
                            print(f"    Data is list with {len(inner_data)} items")
                            if isinstance(inner_data[0], dict):
                                print(f"    First item keys: {list(inner_data[0].keys())}")
                                
                except json.JSONDecodeError:
                    print(f"    Non-JSON response: {response.text[:100]}...")
            else:
                print(f"    Error: {response.text[:100]}")
                
        except Exception as e:
            print(f"    Failed: {e}")

def main():
    """Main test function"""
    print("Skydio WebSocket Telemetry Test")
    print("=" * 50)
    
    try:
        # Test WebSocket connections
        asyncio.run(test_websocket_connection())
        
        # Test REST alternatives
        asyncio.run(test_alternative_approach())
        
    except KeyboardInterrupt:
        print("\nTest interrupted by user")
    except Exception as e:
        print(f"\nTest failed: {e}")

if __name__ == "__main__":
    main()
