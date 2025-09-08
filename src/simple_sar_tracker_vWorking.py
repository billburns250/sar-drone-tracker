"""
Simple SAR Drone Tracker - Direct approach without complex async structure
Based on the working websocket test pattern
"""

import os
import asyncio
import websockets
import json
import requests
import time
from dotenv import load_dotenv

load_dotenv()

class SimpleDroneTracker:
    def __init__(self):
        self.api_token = os.getenv('API_TOKEN')
        self.caltopo_connect_key = os.getenv('CALTOPO_CONNECT_KEY')
        self.drone_serials = [s.strip() for s in os.getenv('DRONE_SERIALS', '').split(',') if s.strip()]
        
        if not all([self.api_token, self.caltopo_connect_key, self.drone_serials]):
            raise ValueError("Missing required environment variables")
    
    def _generate_device_id(self, serial: str) -> str:
        """Generate CalTopo device ID from drone serial number"""
        last_four = serial[-4:] if len(serial) >= 4 else serial
        return f"sccssar_uas-{last_four}"
    
    def _update_caltopo_position(self, device_id: str, latitude: float, longitude: float, altitude=None) -> bool:
        """Update position in CalTopo Connect tracking - CORRECT FORMAT"""
        try:
            # CalTopo Connect format: 
            # https://caltopo.com/api/v1/position/report/{CONNECT_KEY}?id={DEVICE_ID}&lat={LAT}&lng={LNG}
            # Example: https://caltopo.com/api/v1/position/report/sccssar_uas?id=ocd7&lat=36.47375&lng=-118.85302
            
            # Extract just the device identifier (last 4 digits) from full device_id
            device_identifier = device_id.split('-')[-1]  # "sccssar_uas-ocd7" -> "ocd7"
            
            params = {
                "id": device_identifier,  # Just "ocd7", not "sccssar_uas-ocd7"
                "lat": latitude,
                "lng": longitude
            }
            
            if altitude is not None:
                params["alt"] = altitude
                
            # Connect key in URL path, device ID in query parameter
            url = f"https://caltopo.com/api/v1/position/report/{self.caltopo_connect_key}"
            
            print(f"🔧 CalTopo: {url}?{requests.compat.urlencode(params)}")
            
            response = requests.get(url, params=params, timeout=10)
            
            print(f"   Status: {response.status_code} | Response: {response.text[:100]}")
            
            if response.status_code == 200:
                return True
            else:
                print(f"   ❌ CalTopo failed: HTTP {response.status_code}")
                return False
                
        except Exception as e:
            print(f"   💥 CalTopo error: {e}")
            return False
    
    def _check_drone_status(self, serial: str):
        """Check current status of a drone"""
        try:
            headers = {"Accept": "application/json", "Authorization": f"ApiToken {self.api_token}"}
            response = requests.get("https://api.skydio.com/api/v0/vehicles", headers=headers, timeout=15)
            
            if response.status_code == 200:
                data = response.json()
                if data.get("status_code") == 200:
                    vehicles = data.get("data", {}).get("vehicles", [])
                    for vehicle in vehicles:
                        if vehicle.get("vehicle_serial") == serial:
                            return vehicle
            return None
        except:
            return None

async def track_single_drone(tracker, serial):
    """Track a single drone using the proven working pattern"""
    
    device_id = tracker._generate_device_id(serial)
    url = f"wss://stream.skydio.com/data/{serial}"
    
    print(f"Starting tracking for {serial} -> {device_id}")
    
    # Check drone status first
    status = tracker._check_drone_status(serial)
    if status:
        print(f"✅ Found {serial}: {status.get('name', 'Unknown')} | Flight: {status.get('flight_status', 'Unknown')} | Online: {status.get('is_online', False)}")
    else:
        print(f"❌ Could not find drone {serial}")
        return
    
    # Connect to WebSocket using exact pattern from working test
    headers = {"Authorization": f"ApiToken {tracker.api_token}"}
    
    retry_count = 0
    max_retries = 3
    
    while retry_count < max_retries:
        try:
            print(f"🔗 Connecting to {url}...")
            
            async with websockets.connect(url, additional_headers=headers) as websocket:
                print(f"✅ Connected to {serial}")
                
                message_count = 0
                start_time = time.time()
                
                # Use exact same message receiving pattern as working test
                async for message in websocket:
                    try:
                        message_count += 1
                        elapsed = time.time() - start_time
                        
                        # Parse telemetry
                        data = json.loads(message)
                        msg_type = data.get('type', 'unknown')
                        
                        # Extract GPS
                        lat = data.get('lat')
                        lon = data.get('lon')
                        
                        if lat is not None and lon is not None:
                            latitude = float(lat)
                            longitude = float(lon)
                            alt_msl = data.get('alt_msl')
                            altitude = float(alt_msl) if alt_msl else None
                            
                            # Update CalTopo
                            success = tracker._update_caltopo_position(device_id, latitude, longitude, altitude)
                            
                            # Display update
                            battery = data.get('battery', 0)
                            if battery and battery <= 1.0:
                                battery *= 100
                            speed = data.get('speed', 0)
                            sats = data.get('gps_satellites_used', 0)
                            
                            status_icon = "📍" if success else "❌"
                            alt_str = f", alt={altitude:.1f}m" if altitude else ""
                            
                            print(f"{status_icon} {device_id}: {latitude:.6f}, {longitude:.6f}{alt_str} | Batt: {battery:.1f}% | Speed: {speed:.1f}m/s | Sats: {sats} | Msg #{message_count}")
                            
                            if not success:
                                print(f"   ⚠️ CalTopo update failed")
                        else:
                            print(f"📊 {device_id}: {msg_type} message #{message_count} (no GPS)")
                            
                    except json.JSONDecodeError:
                        print(f"❌ Invalid JSON from {serial}")
                    except Exception as e:
                        print(f"❌ Error processing message: {e}")
                        
        except websockets.exceptions.ConnectionClosed:
            print(f"🔌 Connection closed for {serial}")
            retry_count += 1
        except Exception as e:
            print(f"❌ Connection error for {serial}: {e}")
            retry_count += 1
            
        if retry_count < max_retries:
            wait_time = 2 ** retry_count
            print(f"⏳ Retrying {serial} in {wait_time}s...")
            await asyncio.sleep(wait_time)
    
    print(f"💔 Max retries exceeded for {serial}")

async def main():
    """Main tracking function"""
    
    try:
        tracker = SimpleDroneTracker()
        
        print("🚁 Simple SAR Drone Tracker")
        print(f"📡 Tracking: {tracker.drone_serials}")
        print(f"🗂️ Device IDs: {[tracker._generate_device_id(s) for s in tracker.drone_serials]}")
        print("=" * 60)
        
        # Create tasks for each drone
        tasks = []
        for serial in tracker.drone_serials:
            task = asyncio.create_task(track_single_drone(tracker, serial))
            tasks.append(task)
        
        # Run all drone tracking tasks
        await asyncio.gather(*tasks, return_exceptions=True)
        
    except ValueError as e:
        print(f"❌ Configuration Error: {e}")
        print("\nRequired environment variables:")
        print("  API_TOKEN=your_skydio_api_token")
        print("  CALTOPO_CONNECT_KEY=your_caltopo_connect_key") 
        print("  DRONE_SERIALS=serial1,serial2,serial3")
    except KeyboardInterrupt:
        print("\n🛑 Stopped by user")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())
