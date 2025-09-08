"""
SAR Drone Tracking Service - FIXED VERSION
Polls Skydio API for drone positions and updates CalTopo Connect tracking
"""

import os
import time
import logging
import json
import requests
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class DroneTrackingService:
    """Main service for polling Skydio and updating CalTopo Connect tracking"""
    
    def __init__(self):
        # Set up logging with popular format (structured JSON-like)
        self._setup_logging()
        
        # Load configuration
        self.api_token = os.getenv('API_TOKEN')
        self.caltopo_connect_key = os.getenv('CALTOPO_CONNECT_KEY')
        self.drone_serials = self._parse_drone_serials()
        self.poll_interval = int(os.getenv('POLL_INTERVAL_SECONDS', '10'))
        
        # Service state
        self.drone_status = {}  # Track online/offline status
        self.error_counts = {}  # Track consecutive errors for backoff
        self.last_positions = {}  # Track last known positions
        self.vehicle_cache = {}  # Cache serial -> vehicle_id mapping
        
        # Validate configuration
        self._validate_config()
        
        self.logger.info("SAR Drone Tracking Service initialized", extra={
            'action': 'service_start',
            'drones_configured': len(self.drone_serials),
            'poll_interval': self.poll_interval
        })
    
    def _setup_logging(self):
        """Configure logging with structured format"""
        # Enable debug logging during startup to troubleshoot API issues
        logging.basicConfig(
            level=logging.DEBUG,  # Changed to DEBUG for troubleshooting
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
        """Make request to Skydio API - FIXED"""
        try:
            headers = {
                "Accept": "application/json",
                "Authorization": f"ApiToken {self.api_token}"
            }
            
            # FIX 1: Use correct base URL pattern from working example
            url = f"https://api.skydio.com/api/{endpoint}"
            self.logger.debug(f"Making Skydio request to: {url}")
            
            response = requests.get(url, headers=headers, timeout=15)
            self.logger.debug(f"Skydio response status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                self.logger.debug(f"Skydio response data keys: {data.keys()}")
                
                # FIX 2: Handle Skydio's nested response format correctly
                if data.get("status_code") == 200:
                    return data.get("data", {})
                else:
                    error_msg = data.get("error_message", "Unknown error")
                    self.logger.error(f"Skydio API error: {error_msg}")
                    return None
            else:
                self.logger.error(f"Skydio HTTP error: {response.status_code}")
                self.logger.error(f"Response text: {response.text}")
                return None
                
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Skydio request failed: {str(e)}")
            return None
        except json.JSONDecodeError as e:
            self.logger.error(f"Skydio JSON decode error: {str(e)}")
            return None
    
    def _get_vehicle_id_from_serial(self, serial: str) -> Optional[str]:
        """Get vehicle ID from serial number with caching - FIXED"""
        
        # Check cache first
        if serial in self.vehicle_cache:
            return self.vehicle_cache[serial]
        
        # FIX 3: Use correct vehicles endpoint
        vehicles_data = self._make_skydio_request("v0/vehicles")
        if not vehicles_data:
            self.logger.error("Failed to get vehicles data from Skydio")
            return None
            
        vehicles = vehicles_data.get("vehicles", [])
        self.logger.debug(f"Found {len(vehicles)} vehicles")
        
        # Find vehicle by serial
        for vehicle in vehicles:
            vehicle_serial = vehicle.get("serial_number") or vehicle.get("serial")
            self.logger.debug(f"Checking vehicle: {vehicle_serial} vs {serial}")
            
            if vehicle_serial == serial:
                vehicle_id = vehicle.get("id") or vehicle.get("uuid")
                if vehicle_id:
                    # Cache the mapping
                    self.vehicle_cache[serial] = vehicle_id
                    self.logger.info(f"Found vehicle ID {vehicle_id} for serial {serial}")
                    return vehicle_id
                    
        self.logger.warning(f"No vehicle found with serial {serial}")
        return None
    
    def _get_vehicle_position(self, serial: str) -> Optional[Tuple[float, float, Optional[float]]]:
        """Get current position for a specific vehicle by serial number - FIXED"""
        
        # Get vehicle ID
        vehicle_id = self._get_vehicle_id_from_serial(serial)
        if not vehicle_id:
            self.logger.error(f"Could not find vehicle ID for serial {serial}")
            return None
        
        # FIX 4: Try multiple telemetry endpoints based on Skydio API docs
        telemetry_endpoints = [
            f"v0/vehicles/{vehicle_id}/telemetry/current",
            f"v0/vehicles/{vehicle_id}/telemetry/latest", 
            f"v0/vehicles/{vehicle_id}/telemetry",
            f"v0/vehicles/{vehicle_id}/live_telemetry"
        ]
        
        for endpoint in telemetry_endpoints:
            self.logger.debug(f"Trying telemetry endpoint: {endpoint}")
            telemetry_data = self._make_skydio_request(endpoint)
            
            if telemetry_data:
                self.logger.debug(f"Got telemetry data from {endpoint}: {telemetry_data.keys()}")
                position = self._extract_position(telemetry_data)
                if position:
                    return position
        
        # FIX 5: If no live telemetry, try recent flight data
        self.logger.debug("No live telemetry, trying recent flights...")
        flights_data = self._make_skydio_request(f"v0/flights?vehicle_id={vehicle_id}&limit=1")
        
        if flights_data and flights_data.get("flights"):
            latest_flight = flights_data["flights"][0]
            flight_id = latest_flight.get("id")
            
            if flight_id:
                # Try to get telemetry from latest flight
                flight_telemetry_endpoints = [
                    f"v0/flights/{flight_id}/telemetry?limit=1",
                    f"v0/flights/{flight_id}/telemetry/latest"
                ]
                
                for endpoint in flight_telemetry_endpoints:
                    telemetry_data = self._make_skydio_request(endpoint)
                    if telemetry_data:
                        position = self._extract_position(telemetry_data)
                        if position:
                            self.logger.info(f"Got position from recent flight for {serial}")
                            return position
        
        self.logger.warning(f"No position data available for vehicle {serial} ({vehicle_id})")
        return None
    
    def _extract_position(self, telemetry_data: Dict) -> Optional[Tuple[float, float, Optional[float]]]:
        """Extract lat/lon/alt from telemetry data - FIXED"""
        
        if not telemetry_data:
            return None
        
        self.logger.debug(f"Extracting position from telemetry data: {telemetry_data.keys()}")
        
        # FIX 6: Handle multiple possible telemetry data formats
        # Try various possible data structures based on Skydio API
        
        # Format 1: Direct telemetry object
        if "latitude" in telemetry_data and "longitude" in telemetry_data:
            lat = telemetry_data.get("latitude")
            lon = telemetry_data.get("longitude")
            alt = telemetry_data.get("altitude") or telemetry_data.get("altitude_msl") or telemetry_data.get("altitude_agl")
            
            if lat is not None and lon is not None:
                return (float(lat), float(lon), float(alt) if alt is not None else None)
        
        # Format 2: GPS/position nested object
        for key in ["gps", "position", "location", "coordinates"]:
            if key in telemetry_data:
                pos_data = telemetry_data[key]
                if isinstance(pos_data, dict):
                    lat = pos_data.get("latitude") or pos_data.get("lat")
                    lon = pos_data.get("longitude") or pos_data.get("lng") or pos_data.get("lon")
                    alt = pos_data.get("altitude") or pos_data.get("alt")
                    
                    if lat is not None and lon is not None:
                        return (float(lat), float(lon), float(alt) if alt is not None else None)
        
        # Format 3: Telemetry array/list
        if "telemetry" in telemetry_data:
            telemetry_list = telemetry_data["telemetry"]
            if isinstance(telemetry_list, list) and telemetry_list:
                # Use most recent telemetry point
                latest = telemetry_list[-1]
                return self._extract_position(latest)
        
        # Format 4: Points array
        if "points" in telemetry_data:
            points = telemetry_data["points"]
            if isinstance(points, list) and points:
                latest = points[-1]
                return self._extract_position(latest)
        
        # Format 5: Data wrapper
        if "data" in telemetry_data:
            return self._extract_position(telemetry_data["data"])
        
        self.logger.debug(f"Could not extract position from telemetry structure: {telemetry_data}")
        return None
    
    def _update_caltopo_position(self, device_id: str, latitude: float, longitude: float, 
                                altitude: Optional[float] = None) -> bool:
        """Update position in CalTopo Connect tracking"""
        try:
            # CalTopo Connect API format: GET request with query parameters
            # https://caltopo.com/api/v1/position/report/{CONNECT_KEY}?id={DEVICE_ID}&lat={LAT}&lng={LNG}
            
            params = {
                "id": device_id,
                "lat": latitude,
                "lng": longitude
            }
            
            if altitude is not None:
                params["alt"] = altitude
                
            url = f"https://caltopo.com/api/v1/position/report/{self.caltopo_connect_key}"
            
            self.logger.debug(f"Updating CalTopo: {url} with params: {params}")
            
            response = requests.get(url, params=params, timeout=10)
            
            if response.status_code == 200:
                self.logger.debug(f"CalTopo update successful for {device_id}")
                return True
            else:
                self.logger.error(f"CalTopo update failed for {device_id}: HTTP {response.status_code}")
                if response.text:
                    self.logger.error(f"CalTopo error response: {response.text}")
                return False
                
        except requests.exceptions.RequestException as e:
            self.logger.error(f"CalTopo request failed for {device_id}: {str(e)}")
            return False
    
    def _handle_drone_status_change(self, serial: str, is_online: bool):
        """Handle drone coming online or going offline"""
        device_id = self._generate_device_id(serial)
        
        if is_online and self.drone_status.get(serial) != 'online':
            self.logger.info("Drone came online", extra={
                'action': 'drone_online',
                'serial': serial,
                'device_id': device_id
            })
            print(f"✅ Drone {serial} ({device_id}) is now ONLINE")
            
        elif not is_online and self.drone_status.get(serial) != 'offline':
            self.logger.warning("Drone went offline", extra={
                'action': 'drone_offline',
                'serial': serial,
                'device_id': device_id
            })
            print(f"❌ Drone {serial} ({device_id}) is now OFFLINE")
            
        self.drone_status[serial] = 'online' if is_online else 'offline'
    
    def _get_poll_delay(self, serial: str) -> int:
        """Get polling delay with backoff for errors"""
        error_count = self.error_counts.get(serial, 0)
        
        if error_count == 0:
            return self.poll_interval
        elif error_count < 3:
            return self.poll_interval * 2  # Double delay
        else:
            return self.poll_interval * 4  # Quadruple delay for persistent errors
    
    def _poll_drone(self, serial: str):
        """Poll a single drone and update its position"""
        device_id = self._generate_device_id(serial)
        
        self.logger.debug(f"Polling drone {serial} (device_id: {device_id})")
        
        try:
            # Get current position from Skydio
            position = self._get_vehicle_position(serial)
            
            if position:
                latitude, longitude, altitude = position
                
                self.logger.info(f"Got position for {serial}: {latitude:.6f}, {longitude:.6f}, alt={altitude}")
                
                # Update CalTopo tracking
                success = self._update_caltopo_position(device_id, latitude, longitude, altitude)
                
                if success:
                    # Reset error count on success
                    self.error_counts[serial] = 0
                    self.last_positions[serial] = position
                    self._handle_drone_status_change(serial, True)
                    
                    # Log successful update (minimal)
                    print(f"📍 {device_id}: {latitude:.6f}, {longitude:.6f}")
                    
                else:
                    # CalTopo update failed
                    self.error_counts[serial] = self.error_counts.get(serial, 0) + 1
                    self.logger.error("CalTopo update failed", extra={
                        'action': 'caltopo_update_failed',
                        'serial': serial,
                        'device_id': device_id,
                        'error_count': self.error_counts[serial]
                    })
                    print(f"⚠️  CalTopo update failed for {device_id}")
                    
            else:
                # Skydio position unavailable
                self.error_counts[serial] = self.error_counts.get(serial, 0) + 1
                self._handle_drone_status_change(serial, False)
                
                self.logger.error("Skydio position unavailable", extra={
                    'action': 'skydio_position_failed',
                    'serial': serial,
                    'device_id': device_id,
                    'error_count': self.error_counts[serial]
                })
                
        except Exception as e:
            self.error_counts[serial] = self.error_counts.get(serial, 0) + 1
            self.logger.error(f"Drone polling error for {serial}: {str(e)}", extra={
                'action': 'polling_error',
                'serial': serial,
                'error_count': self.error_counts[serial]
            })
    
    def run(self):
        """Main service loop"""
        self.logger.info("Starting drone tracking service", extra={
            'action': 'service_start',
            'drones': self.drone_serials
        })
        
        print(f"🚁 SAR Drone Tracking Service Started")
        print(f"📡 Polling {len(self.drone_serials)} drones every {self.poll_interval} seconds")
        print(f"🗂️  Device IDs: {[self._generate_device_id(s) for s in self.drone_serials]}")
        print("=" * 60)
        
        try:
            cycle = 0
            while True:
                cycle += 1
                
                # Stagger requests across the polling interval
                delay_between_drones = self.poll_interval / len(self.drone_serials) if self.drone_serials else 1
                
                for i, serial in enumerate(self.drone_serials):
                    # Add stagger delay
                    if i > 0:
                        time.sleep(delay_between_drones)
                    
                    # Check if we should use error backoff for this drone
                    poll_delay = self._get_poll_delay(serial)
                    if cycle % (poll_delay // self.poll_interval) == 0:
                        self._poll_drone(serial)
                
                # Wait for next polling cycle
                remaining_time = self.poll_interval - (delay_between_drones * len(self.drone_serials))
                if remaining_time > 0:
                    time.sleep(remaining_time)
                    
        except KeyboardInterrupt:
            self.logger.info("Service stopped by user", extra={'action': 'service_stop'})
            print("\n🛑 Service stopped by user")
            
        except Exception as e:
            self.logger.error(f"Service crashed: {str(e)}", extra={'action': 'service_crash'})
            print(f"\n💥 Service crashed: {str(e)}")
            raise


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
