"""
SAR Drone Tracking Service
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
    
    def _get_vehicle_position(self, serial: str) -> Optional[Tuple[float, float, Optional[float]]]:
        """Get current position for a specific vehicle by serial number"""
        
        # First get vehicle ID from serial
        vehicles_data = self._make_skydio_request("v0/vehicles")
        if not vehicles_data:
            return None
            
        vehicles = vehicles_data.get("vehicles", [])
        vehicle_id = None
        
        for vehicle in vehicles:
            if vehicle.get("serial_number") == serial:
                vehicle_id = vehicle.get("id")
                break
                
        if not vehicle_id:
            return None
            
        # Get live telemetry for this vehicle
        telemetry_data = self._make_skydio_request(f"v0/vehicles/{vehicle_id}/telemetry")
        if not telemetry_data:
            return None
            
        # Extract position from telemetry
        return self._extract_position(telemetry_data)
    
    def _extract_position(self, telemetry: Dict) -> Optional[Tuple[float, float, Optional[float]]]:
        """Extract latitude, longitude, altitude from telemetry data"""
        try:
            # Try common field names
            lat_fields = ["latitude", "lat", "gps_latitude", "position_lat"]
            lon_fields = ["longitude", "lon", "lng", "gps_longitude", "position_lon"]
            alt_fields = ["altitude", "alt", "gps_altitude", "elevation"]
            
            latitude = longitude = altitude = None
            
            for field in lat_fields:
                if field in telemetry and telemetry[field] is not None:
                    latitude = float(telemetry[field])
                    break
                    
            for field in lon_fields:
                if field in telemetry and telemetry[field] is not None:
                    longitude = float(telemetry[field])
                    break
                    
            for field in alt_fields:
                if field in telemetry and telemetry[field] is not None:
                    altitude = float(telemetry[field])
                    break
            
            if latitude is not None and longitude is not None:
                return (latitude, longitude, altitude)
                
            return None
            
        except (ValueError, TypeError) as e:
            self.logger.error(f"Position extraction error: {str(e)}")
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
        
        print(f"DEBUG: _poll_drone called with serial: {serial}")
        self.logger.info(f"Polling drone {serial} (device_id: {device_id})")
        
        try:
            # Get current position from Skydio
            print(f"DEBUG: About to call _get_vehicle_position for {serial}")
            position = self._get_vehicle_position(serial)
            print(f"DEBUG: _get_vehicle_position returned: {position}")
            
            if position:
                latitude, longitude, altitude = position
                
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
                print(f"DEBUG: Position was None for {serial}")
                self.error_counts[serial] = self.error_counts.get(serial, 0) + 1
                self._handle_drone_status_change(serial, False)
                
                self.logger.error("Skydio position unavailable", extra={
                    'action': 'skydio_position_failed',
                    'serial': serial,
                    'device_id': device_id,
                    'error_count': self.error_counts[serial]
                })
                
        except Exception as e:
            print(f"DEBUG: Exception in _poll_drone: {str(e)}")
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
