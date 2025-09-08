"""
Simple WebSocket debug script to isolate the message receiving issue
"""

import os
import asyncio
import websockets
import json
import time
from dotenv import load_dotenv

load_dotenv()

async def simple_telemetry_test():
    """Simple test to receive messages from Skydio WebSocket"""
    
    api_token = os.getenv('API_TOKEN')
    serial = "sim-k8x4ocd7"
    url = f"wss://stream.skydio.com/data/{serial}"
    
    print(f"Connecting to: {url}")
    
    headers = {"Authorization": f"ApiToken {api_token}"}
    
    try:
        async with websockets.connect(url, additional_headers=headers) as websocket:
            print("✅ Connected successfully!")
            
            message_count = 0
            start_time = time.time()
            
            print("Waiting for messages...")
            
            # Try to receive up to 5 messages or timeout after 60 seconds
            while message_count < 5:
                try:
                    # Wait for message with 60 second timeout
                    message = await asyncio.wait_for(websocket.recv(), timeout=60.0)
                    
                    message_count += 1
                    elapsed = time.time() - start_time
                    
                    print(f"\n📨 Message #{message_count} (after {elapsed:.1f}s):")
                    print(f"   Raw length: {len(message)} bytes")
                    
                    try:
                        data = json.loads(message)
                        print(f"   Type: {data.get('type', 'unknown')}")
                        print(f"   Keys: {list(data.keys())}")
                        
                        # Check for GPS data
                        if 'lat' in data and 'lon' in data:
                            print(f"   📍 GPS: {data['lat']}, {data['lon']}")
                        else:
                            print("   ❌ No GPS data found")
                            
                        # Show full message for first one
                        if message_count == 1:
                            print(f"   Full message: {json.dumps(data, indent=2)}")
                            
                    except json.JSONDecodeError:
                        print(f"   ❌ Not valid JSON: {message[:100]}...")
                        
                except asyncio.TimeoutError:
                    print(f"\n⏰ Timeout after 60 seconds - no messages received")
                    break
                except Exception as e:
                    print(f"\n❌ Error receiving message: {e}")
                    break
            
            if message_count == 0:
                print("\n❌ No messages received at all")
                
                # Try sending a ping to test connection
                try:
                    print("Testing connection with ping...")
                    pong = await websocket.ping()
                    await asyncio.wait_for(pong, timeout=5)
                    print("✅ Ping successful - connection is alive")
                except Exception as e:
                    print(f"❌ Ping failed: {e}")
            else:
                print(f"\n✅ Successfully received {message_count} messages")
                
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        import traceback
        traceback.print_exc()

def main():
    print("Simple Skydio WebSocket Debug")
    print("=" * 40)
    
    try:
        asyncio.run(simple_telemetry_test())
    except KeyboardInterrupt:
        print("\n🛑 Interrupted by user")
    except Exception as e:
        print(f"\n💥 Failed: {e}")

if __name__ == "__main__":
    main()
