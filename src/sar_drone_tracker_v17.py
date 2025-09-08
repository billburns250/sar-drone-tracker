"""
SAR Drone Tracking Service - WebSocket Live Telemetry Version
Connects to Skydio WebSocket streams for real-time GPS and updates CalTopo Connect tracking
"""

import os
import time
import logging
import json
import asyncio
import websockets
import requests
import threading
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class DroneTrackingService:
    """Main service for live telemetry tracking via WebSocket and CalTopo updates"""
    
    def __init__(self):
        # Set up logging
        self._setup_logging()
        
        # Load configuration
        self.api_token = os.getenv('API_TOKEN')
        self.caltopo_connect_key = os.getenv('CALTOPO_CONNECT_KEY')
        self.drone_serials = self._parse_drone_serials()
        self.poll_interval = int(os.getenv('POLL_INTERVAL_SECONDS', '10'))
        
        # Service state
        self.drone_status = {}  # Track online/offline status
        self.active_connections = {}  # Track WebSocket connections
        self.last_positions = {}  # Track last known positions
        self.running = False
        
        # Validate configuration
        self._validate_config()
        
        self.logger.info("SAR Drone Tracking Service initialized", extra={
            'action': 'service_start',
            'drones_configured': len(self.drone_serials),
            'poll_interval': self.poll_interval
        })
    
    def _setup_logging(self):
        """Configure logging with structured format"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.StreamHandler(),
                logging.FileHandler('drone_tracking.log')
            ]
        )
        self.logger = logging.getLogger('DroneTracker')
    
    def _parse_drone_serials(self) -> List[str]:
        """Parse drone serials from environment variable"""
        serials_str = os.getenv('DRONE_SERIALS', '')
        if not serials_str:
            return []
        return [serial.strip() for serial in serials_str.split(',') if serial.strip()]
    
    def _validate_config(self):
        """Validate required configuration"""
        if not self.api_token:
            raise ValueError("API_TOKEN environment variable required")
        
        if not self.caltopo_connect_key:
            raise ValueError("CALTOPO_CONNECT_KEY environment variable required")
            
        if not self.drone_serials:
            raise ValueError("DRONE_SERIALS environment variable required")
            
        self.logger.info("Configuration validated", extra={
            'action': 'config_validated',
            'drones': self.drone_serials
        })
    
    def _generate_device_id(self, serial: str) -> str:
        """Generate CalTopo device ID from drone serial number"""
        last_four = serial[-4:] if len(serial) >= 4 else serial
        return f"sccssar_uas-{last_four}"
    
    def _make_skydio_request(self, endpoint: str) -> Optional[Dict]:
        """Make request to Skydio API"""
        try:
            headers = {
                "Accept": "application/json",
                "Authorization": f"ApiToken {self.api_token}"
            }
            
            url = f"https://api.skydio.com/api/{endpoint}"
            response = requests.get(url, headers=headers, timeout=15)
            
            if response.status_code == 200:
                data = response.json()
                if data.get("status_code") == 200:
                    return data.get("data", {})
                else:
                    error_msg = data.get("error_message", "Unknown error")
                    self.logger.error(f"Skydio API error: {error_msg}")
                    return None
            else:
                self.logger.error(f"Skydio HTTP error: {response.status_code}")
                return None
                
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Skydio request failed: {str(e)}")
            return None
        except json.JSONDecodeError as e:
            self.logger.error(f"Skydio JSON decode error: {str(e)}")
            return None
    
    def _check_drone_status(self, serial: str) -> Dict:
        """Check current status of a drone"""
        vehicles_data = self._make_skydio_request("v0/vehicles")
        if not vehicles_data:
            return {"status": "unknown", "error": "Cannot connect to Skydio API"}
            
        for vehicle in vehicles_data.get("vehicles", []):
            if vehicle.get("vehicle_serial") == serial:
                return {
                    "status": "found",
                    "vehicle_serial": vehicle.get("vehicle_serial"),
                    "name": vehicle.get("name"),
                    "flight_status": vehicle.get("flight_status"),
                    "is_online": vehicle.get("is_online", False),
                    "is_live_streaming": vehicle.get("is_live_streaming", False),
                    "battery_percentage": vehicle.get("battery_status", {}).get("percentage", 0) * 100
                }
                
        return {"status": "not_found", "error": f"Drone {serial} not found in fleet"}
    
    def _get_websocket_url(self, serial: str) -> str:
        """Generate WebSocket URL for live telemetry"""
        return f"wss://stream.skydio.com/data/{serial}"
    
    def _extract_position_from_telemetry(self, telemetry_data: Dict) -> Optional[Tuple[float, float, Optional[float]]]:
        """Extract lat/lon/alt from live telemetry data"""
        
        if not telemetry_data:
            return None
        
        # Try various possible GPS data structures
        for location_key in ["gps", "location", "position", "coordinates"]:
            if location_key in telemetry_data:
                gps_data = telemetry_data[location_key]
                if isinstance(gps_data, dict):
                    lat = gps_data.get("latitude") or gps_data.get("lat")
                    lon = gps_data.get("longitude") or gps_data.get("lng") or gps_data.get("lon")
                    alt = gps_data.get("altitude") or gps_data.get("alt")
                    
                    if lat is not None and lon is not None:
                        return (float(lat), float(lon), float(alt) if alt is not None else None)
        
        # Try direct fields
        if "latitude" in telemetry_data and "longitude" in telemetry_data:
            lat = telemetry_data.get("latitude")
            lon = telemetry_data.get("longitude") 
            alt = telemetry_data.get("altitude")
            
            if lat is not None and lon is not None:
                return (float(lat), float(lon), float(alt) if alt is not None else None)
        
        return None
    
    def _update_caltopo_position(self, device_id: str, latitude: float, longitude: float, 
                                altitude: Optional[float] = None) -> bool:
        """Update position in CalTopo Connect tracking"""
        try:
            params = {
                "id": device_id,
                "lat": latitude,
                "lng": longitude
            }
            
            if altitude is not None:
                params["alt"] = altitude
                
            url = f"https://caltopo.com/api/v1/position/report/{self.caltopo_connect_key}"
            
            response = requests.get(url, params=params, timeout=10)
            
            if response.status_code == 200:
                return True
            else:
                self.logger.error(f"CalTopo update failed for {device_id}: HTTP {response.status_code}")
                if response.text:
                    self.logger.error(f"CalTopo error response: {response.text}")
                return False
                
        except requests.exceptions.RequestException as e:
            self.logger.error(f"CalTopo request failed for {device_id}: {str(e)}")
            return False
    
    async def _handle_websocket_telemetry(self, serial: str):
        """Handle WebSocket connection for live telemetry"""
        device_id = self._generate_device_id(serial)
        websocket_url = self._get_websocket_url(serial)
        
        self.logger.info(f"Connecting to live telemetry for {serial}: {websocket_url}")
        
        retry_count = 0
        max_retries = 5
        
        while self.running and retry_count < max_retries:
            try:
                # Use the working WebSocket URL and auth method from test results
                headers = {
                    "Authorization": f"ApiToken {self.api_token}"
                }
                
                # Fix: Use additional_headers instead of extra_headers (websockets library compatibility)
                async with websockets.connect(websocket_url, additional_headers=headers) as websocket:
                    self.active_connections[serial] = websocket
                    self.logger.info(f"Connected to live stream for {serial}")
                    retry_count = 0  # Reset on successful connection
                    
                    async for message in websocket:
                        if not self.running:
                            break
                            
                        try:
                            # Parse telemetry message
                            telemetry_data = json.loads(message)
                            
                            # Log what we received for debugging
                            msg_type = telemetry_data.get("type", "unknown")
                            self.logger.debug(f"Received {msg_type} message from {serial}")
                            
                            # Extract GPS position
                            position = self._extract_position_from_telemetry(telemetry_data)
                            
                            if position:
                                latitude, longitude, altitude = position
                                
                                # Update CalTopo with live position
                                success = self._update_caltopo_position(device_id, latitude, longitude, altitude)
                                
                                if success:
                                    self.last_positions[serial] = position
                                    self.drone_status[serial] = 'online'
                                    
                                    # Log position update
                                    alt_str = f", alt={altitude:.1f}m" if altitude else ""
                                    battery = telemetry_data.get("battery", 0) * 100
                                    speed = telemetry_data.get("speed", 0)
                                    print(f"📍 LIVE {device_id}: {latitude:.6f}, {longitude:.6f}{alt_str} | Batt: {battery:.1f}% | Speed: {speed:.1f}m/s")
                                    
                                    self.logger.info(f"Position updated for {serial}: {latitude:.6f}, {longitude:.6f}")
                                else:
                                    self.logger.error(f"Failed to update CalTopo for {serial}")
                            else:
                                # Log telemetry without GPS for debugging
                                if msg_type == "status":
                                    self.logger.debug(f"Status message from {serial} (no GPS extracted)")
                                    
                        except json.JSONDecodeError as e:
                            self.logger.error(f"Invalid JSON from {serial}: {e}")
                        except Exception as e:
                            self.logger.error(f"Error processing telemetry for {serial}: {e}")
                            
            except websockets.exceptions.ConnectionClosed:
                self.logger.warning(f"WebSocket connection closed for {serial}")
                retry_count += 1
                
            except websockets.exceptions.WebSocketException as e:
                self.logger.error(f"WebSocket error for {serial}: {e}")
                retry_count += 1
                
            except Exception as e:
                self.logger.error(f"Unexpected error connecting to {serial}: {e}")
                retry_count += 1
            
            if self.running and retry_count < max_retries:
                wait_time = min(2 ** retry_count, 30)  # Exponential backoff, max 30s
                self.logger.info(f"Retrying connection to {serial} in {wait_time} seconds...")
                await asyncio.sleep(wait_time)
        
        # Mark as offline if we've exhausted retries
        if retry_count >= max_retries:
            self.drone_status[serial] = 'offline'
            self.logger.error(f"Max retries exceeded for {serial}, marking offline")
        
        # Clean up connection
        if serial in self.active_connections:
            del self.active_connections[serial]
    
    async def _start_live_tracking(self):
        """Start live tracking for all configured drones"""
        self.logger.info("Starting live telemetry tracking...")
        
        # Create WebSocket tasks for each drone
        tasks = []
        for serial in self.drone_serials:
            task = asyncio.create_task(self._handle_websocket_telemetry(serial))
            tasks.append(task)
        
        # Wait for all tasks (they'll run indefinitely)
        try:
            await asyncio.gather(*tasks, return_exceptions=True)
        except Exception as e:
            self.logger.error(f"Error in live tracking: {e}")
    
    def run(self):
        """Main service entry point"""
        self.running = True
        
        print(f"🚁 SAR Drone Tracking Service Started")
        print(f"📡 Live tracking {len(self.drone_serials)} drones")
        print(f"🗂️  Device IDs: {[self._generate_device_id(s) for s in self.drone_serials]}")
        print("=" * 60)
        
        # Check initial status of all drones
        for serial in self.drone_serials:
            device_id = self._generate_device_id(serial)
            status = self._check_drone_status(serial)
            
            if status["status"] == "found":
                print(f"✅ Found drone: {serial} ({device_id})")
                print(f"   Name: {status.get('name', 'Unknown')}")
                print(f"   Flight Status: {status.get('flight_status', 'Unknown')}")
                print(f"   Online: {status.get('is_online', False)}")
                print(f"   Live Streaming: {status.get('is_live_streaming', False)}")
                print(f"   Battery: {status.get('battery_percentage', 0):.1f}%")
                
                if status.get('is_live_streaming'):
                    print(f"   📡 Will connect to live telemetry stream")
                else:
                    print(f"   ⚠️  Live streaming not active")
            else:
                print(f"❌ {status['error']}")
        
        print("\n🔗 Starting live telemetry connections...")
        print("=" * 60)
        
        try:
            # Start the async WebSocket event loop
            asyncio.run(self._start_live_tracking())
            
        except KeyboardInterrupt:
            self.logger.info("Service stopped by user")
            print("\n🛑 Service stopped by user")
            
        except Exception as e:
            self.logger.error(f"Service crashed: {str(e)}")
            print(f"\n💥 Service crashed: {str(e)}")
            raise
        finally:
            self.running = False


def main():
    """Main entry point"""
    try:
        service = DroneTrackingService()
        service.run()
        
    except ValueError as e:
        print(f"❌ Configuration Error: {str(e)}")
        print("\nRequired environment variables:")
        print("  API_TOKEN=your_skydio_api_token")
        print("  CALTOPO_CONNECT_KEY=your_caltopo_connect_key")
        print("  DRONE_SERIALS=serial1,serial2,serial3")
        print("\nOptional:")
        print("  POLL_INTERVAL_SECONDS=10")
        
    except Exception as e:
        print(f"❌ Service Error: {str(e)}")


if __name__ == "__main__":
    main()
